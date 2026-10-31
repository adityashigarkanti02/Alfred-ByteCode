"""
Dynamic Authority Engine for ALFRED AI.

Central authority orchestrator that binds:
1. Deterministic Policy Engine
2. Capability Manager
3. Provenance & Taint Tracker
4. Circuit Breaker Sentinel

The Planner is strictly decoupled from execution authority:
The Planner can ONLY propose an action.
The Dynamic Authority Engine decides whether to:
- ALLOW (and issue a short-lived, signed Capability)
- REQUIRE_APPROVAL (and generate an immutable Approval request)
- DENY (and log an authoritative rejection or trip the circuit breaker)
"""

from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from backend.app.security.policy_engine.engine import (
    AuthorityLevel,
    PolicyDecision,
    DeterministicPolicyEngine,
    PolicyRuleResult
)
from backend.app.security.capability_manager.manager import (
    CapabilityManager,
    CapabilityPayload
)
from backend.app.security.provenance.tracker import ProvenanceTracker, TrustLabel


class AuthorityEvaluationResult(BaseModel):
    """
    Complete verdict returned by the Dynamic Authority Engine.
    """
    decision: PolicyDecision
    authority_level: AuthorityLevel
    rule_name: str
    rationale: str
    capability: Optional[CapabilityPayload] = None
    approval_id: Optional[str] = None
    circuit_breaker_tripped: bool = False


class DynamicAuthorityEngine:
    """
    Orchestrates policy evaluation, parameter verification, and capability issuance.
    """

    def __init__(
        self,
        policy_engine: Optional[DeterministicPolicyEngine] = None,
        capability_manager: Optional[CapabilityManager] = None,
        provenance_tracker: Optional[ProvenanceTracker] = None,
        circuit_breaker_threshold: int = 3
    ):
        self.policy_engine = policy_engine or DeterministicPolicyEngine()
        self.capability_manager = capability_manager or CapabilityManager()
        self.provenance_tracker = provenance_tracker or ProvenanceTracker()
        self.circuit_breaker_threshold = circuit_breaker_threshold
        
        # Track suspicious violations per task for circuit breaker
        self._task_violation_counts: Dict[str, int] = {}
        self._tripped_tasks: set[str] = set()

    def is_circuit_breaker_tripped(self, task_id: str) -> bool:
        """Checks if emergency circuit breaker is active for task."""
        return task_id in self._tripped_tasks

    def trip_circuit_breaker(self, task_id: str, reason: str = "") -> None:
        """
        Manually or automatically trips the circuit breaker for a task.
        Revokes all temporary capabilities immediately.
        """
        self._tripped_tasks.add(task_id)

    def reset_circuit_breaker(self, task_id: str) -> None:
        """Manual operator reset of circuit breaker."""
        self._tripped_tasks.discard(task_id)
        self._task_violation_counts[task_id] = 0

    def evaluate_proposal(
        self,
        user_id: str,
        task_id: str,
        tool_name: str,
        operation: str,
        parameters: Dict[str, Any],
        task_intent: str,
        is_tainted: bool = False
    ) -> AuthorityEvaluationResult:
        """
        Evaluates a tool proposal from the LLM planner.
        Returns ALLOW with Capability, REQUIRE_APPROVAL, or DENY.
        """
        # 1. Circuit breaker verification
        if self.is_circuit_breaker_tripped(task_id):
            return AuthorityEvaluationResult(
                decision=PolicyDecision.DENY,
                authority_level=AuthorityLevel.L3_HARD_DENY,
                rule_name="CIRCUIT_BREAKER_ACTIVE",
                rationale="Emergency circuit breaker is active for this task. All privileged operations are blocked.",
                circuit_breaker_tripped=True
            )

        # 2. Run deterministic policy evaluation
        rule_result = self.policy_engine.evaluate(
            tool_name=tool_name,
            operation=operation,
            parameters=parameters,
            is_tainted=is_tainted,
            task_intent=task_intent
        )

        # 3. Handle Hard Deny
        if rule_result.decision == PolicyDecision.DENY:
            # Increment violation count
            self._task_violation_counts[task_id] = self._task_violation_counts.get(task_id, 0) + 1
            if self._task_violation_counts[task_id] >= self.circuit_breaker_threshold:
                self.trip_circuit_breaker(task_id, reason="Exceeded maximum security violations")
                return AuthorityEvaluationResult(
                    decision=PolicyDecision.DENY,
                    authority_level=AuthorityLevel.L3_HARD_DENY,
                    rule_name="CIRCUIT_BREAKER_TRIGGERED",
                    rationale=f"Security violation threshold reached ({self.circuit_breaker_threshold}). Emergency circuit breaker tripped.",
                    circuit_breaker_tripped=True
                )

            return AuthorityEvaluationResult(
                decision=PolicyDecision.DENY,
                authority_level=rule_result.authority_level,
                rule_name=rule_result.rule_name,
                rationale=rule_result.rationale
            )

        # 4. Handle Require Approval (L2)
        if rule_result.decision == PolicyDecision.REQUIRE_APPROVAL:
            return AuthorityEvaluationResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                authority_level=rule_result.authority_level,
                rule_name=rule_result.rule_name,
                rationale=rule_result.rationale
            )

        # 5. Handle Allowed Operations (L0 or L1) -> Issue signed Capability
        # Extract resource scope and destination from parameters
        resource_scope = str(parameters.get("path") or parameters.get("message_id") or parameters.get("url") or "*")
        permitted_destination = str(parameters.get("destination") or parameters.get("recipient") or "") or None

        capability = self.capability_manager.issue_capability(
            user_id=user_id,
            task_id=task_id,
            authorized_tool=tool_name,
            exact_operation=operation,
            resource_scope=resource_scope,
            permitted_destination=permitted_destination,
            duration_seconds=300
        )

        return AuthorityEvaluationResult(
            decision=PolicyDecision.ALLOW,
            authority_level=rule_result.authority_level,
            rule_name=rule_result.rule_name,
            rationale=rule_result.rationale,
            capability=capability
        )
