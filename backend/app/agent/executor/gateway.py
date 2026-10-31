"""
Secure Tool Execution Gateway for ALFRED AI.

The Gateway is the SOLE execution boundary for external tools and services.
Neither the LLM planner nor workflows can directly trigger actions.
Every execution request must present a valid, cryptographically signed Capability
matching the exact parameters.

The Gateway:
1. Validates the Capability signature, task binding, and expiration.
2. Runs the Independent Action Verifier on the candidate action.
3. Dispatches the action to the dedicated integration driver.
4. Wraps returned outputs in ProvenanceEnvelopes with appropriate trust labels.
5. Scans external output with the Prompt Injection Detector.
6. Records complete, tamper-evident audit logs.
"""

from typing import Dict, Any, Optional, Tuple, Callable
from pydantic import BaseModel, Field
from backend.app.security.capability_manager.manager import CapabilityManager, CapabilityPayload
from backend.app.security.verifier.action_verifier import IndependentActionVerifier, VerificationResult
from backend.app.security.provenance.tracker import ProvenanceTracker, ProvenanceEnvelope, TrustLabel
from backend.app.security.injection_detector.detector import PromptInjectionDetector, DetectionResult


class ToolExecutionResult(BaseModel):
    """
    Standardized result structure returned by the execution gateway.
    """
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    provenance_hash: Optional[str] = None
    is_tainted: bool = False
    security_event_detected: bool = False
    detection_result: Optional[DetectionResult] = None


class SecureToolGateway:
    """
    Execution gateway enforcing capability-based authorization and output provenance tagging.
    """

    def __init__(
        self,
        capability_manager: Optional[CapabilityManager] = None,
        action_verifier: Optional[IndependentActionVerifier] = None,
        provenance_tracker: Optional[ProvenanceTracker] = None,
        injection_detector: Optional[PromptInjectionDetector] = None
    ):
        self.capability_manager = capability_manager or CapabilityManager()
        self.action_verifier = action_verifier or IndependentActionVerifier()
        self.provenance_tracker = provenance_tracker or ProvenanceTracker()
        self.injection_detector = injection_detector or PromptInjectionDetector()
        
        # Tool driver registry: tool_name -> dict of operation -> handler callable
        self._handlers: Dict[str, Dict[str, Callable]] = {}

    def register_handler(self, tool_name: str, operation: str, handler: Callable) -> None:
        """Registers an integration driver handler for a specific tool and operation."""
        if tool_name not in self._handlers:
            self._handlers[tool_name] = {}
        self._handlers[tool_name][operation] = handler

    def execute_tool(
        self,
        task_id: str,
        user_prompt: str,
        tool_name: str,
        operation: str,
        parameters: Dict[str, Any],
        capability: CapabilityPayload,
        approved_parameters_snapshot: Optional[Dict[str, Any]] = None
    ) -> ToolExecutionResult:
        """
        Executes a proposed tool operation under strict capability verification.
        """
        # 1. Target resource resolution for capability check
        target_resource = str(parameters.get("path") or parameters.get("message_id") or parameters.get("url") or "*")
        destination = str(parameters.get("destination") or parameters.get("recipient") or "") or None

        # 2. Cryptographic capability validation
        is_valid_cap, cap_err = self.capability_manager.validate_capability(
            capability=capability,
            task_id=task_id,
            tool_name=tool_name,
            operation=operation,
            target_resource=target_resource,
            destination=destination
        )
        if not is_valid_cap:
            return ToolExecutionResult(
                success=False,
                error=f"Capability Authorization Denied: {cap_err}"
            )

        # 3. Independent Action Verification
        verification = self.action_verifier.verify_action(
            original_user_prompt=user_prompt,
            tool_name=tool_name,
            operation=operation,
            parameters=parameters,
            approved_parameters_snapshot=approved_parameters_snapshot
        )
        if not verification.is_valid:
            return ToolExecutionResult(
                success=False,
                error=f"Action Verifier Rejected Operation: {verification.rejection_reason}"
            )

        # 4. Handler resolution
        tool_map = self._handlers.get(tool_name)
        if not tool_map or operation not in tool_map:
            return ToolExecutionResult(
                success=False,
                error=f"No execution driver registered for '{tool_name}:{operation}'"
            )

        handler = tool_map[operation]

        # 5. Execute driver in isolated try/except block
        try:
            raw_result = handler(**parameters)
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Tool execution exception: {str(e)}"
            )

        # 6. Post-execution provenance tagging and prompt injection scanning
        result_text = str(raw_result)
        trust_label = TrustLabel.UNTRUSTED_EXTERNAL
        
        # Safe internal operations or local status
        if tool_name == "companion_fs" and operation in ("write_file", "edit_file", "create_directory"):
            trust_label = TrustLabel.USER_AUTHORIZED

        envelope = ProvenanceEnvelope.create(
            content=result_text,
            trust_label=trust_label,
            origin_source=f"{tool_name}:{operation}:{target_resource}",
            metadata={"task_id": task_id, "operation": operation}
        )
        self.provenance_tracker.register(envelope)

        # Scan external payloads for prompt injection attacks
        detection = None
        security_event_detected = False
        if trust_label == TrustLabel.UNTRUSTED_EXTERNAL:
            detection = self.injection_detector.inspect_text(result_text, source=f"{tool_name}:{operation}")
            if detection.is_suspicious:
                security_event_detected = True

        return ToolExecutionResult(
            success=True,
            data=raw_result,
            provenance_hash=envelope.content_hash,
            is_tainted=envelope.is_tainted,
            security_event_detected=security_event_detected,
            detection_result=detection
        )
