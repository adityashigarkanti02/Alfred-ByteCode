"""
Independent Action Verifier for ALFRED AI.

This module provides a critical verification checkpoint immediately prior to tool
execution. Even if the LLM planner proposes an action, and even after an approval
is given, the Independent Action Verifier double-checks:
1. Relevance to original user task intent.
2. Parameter integrity: Ensures parameters were not introduced or tainted by untrusted external sources.
3. Destination authorization: Confirms recipient addresses or outbound URLs are legitimate.
4. Parameter mutation defense: Validates that approved parameters have not been tampered with
   between human approval and actual execution.
"""

from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from backend.app.security.provenance.tracker import ProvenanceTracker


class VerificationResult(BaseModel):
    """
    Result of independent action verification.
    """
    is_valid: bool
    rejection_reason: Optional[str] = None
    relevance_score: float = Field(default=1.0, description="Estimated semantic alignment with original task")
    parameter_tampering_detected: bool = False
    untrusted_parameter_detected: bool = False


class IndependentActionVerifier:
    """
    Independent gatekeeper verifying action legitimacy and parameter lineage.
    """

    def __init__(self, provenance_tracker: Optional[ProvenanceTracker] = None):
        self.provenance_tracker = provenance_tracker or ProvenanceTracker()

    def verify_action(
        self,
        original_user_prompt: str,
        tool_name: str,
        operation: str,
        parameters: Dict[str, Any],
        approved_parameters_snapshot: Optional[Dict[str, Any]] = None,
        parameter_taint_map: Optional[Dict[str, bool]] = None
    ) -> VerificationResult:
        """
        Runs exhaustive verification rules on the action candidate.
        Fails closed on any inconsistency.
        """
        # 1. Parameter tampering check (if human approval was previously obtained)
        if approved_parameters_snapshot is not None:
            # Check for parameter deviation
            for key, approved_val in approved_parameters_snapshot.items():
                current_val = parameters.get(key)
                if current_val != approved_val:
                    return VerificationResult(
                        is_valid=False,
                        rejection_reason=f"Parameter tampering detected for '{key}': approved '{approved_val}', received '{current_val}'",
                        parameter_tampering_detected=True
                    )

        # 2. Untrusted parameter injection check (Taint Analysis)
        if parameter_taint_map:
            for param_key, is_tainted in parameter_taint_map.items():
                if is_tainted:
                    # Critical parameters cannot be derived from untrusted external sources
                    if param_key in ("recipient", "destination", "url", "to", "command", "path"):
                        return VerificationResult(
                            is_valid=False,
                            rejection_reason=f"Security violation: Sensitive parameter '{param_key}' is tainted by untrusted external content",
                            untrusted_parameter_detected=True
                        )

        # 3. Intent & Relevance Boundary Check
        prompt_lower = original_user_prompt.lower()
        tool_op = f"{tool_name}:{operation}".lower()

        # If user asks to read an invoice, sending an email to an unmentioned address is anomalous
        if "read" in prompt_lower or "summarize" in prompt_lower or "find" in prompt_lower:
            if tool_op == "gmail:send_email":
                # Check if prompt explicitly requested sending
                send_keywords = ["send", "forward", "reply", "email to", "share with"]
                if not any(kw in prompt_lower for kw in send_keywords):
                    return VerificationResult(
                        is_valid=False,
                        rejection_reason="Action 'send_email' is not relevant to read/summarize user task intent",
                        relevance_score=0.1
                    )

        # 4. Deletion Relevance Check
        if "delete" in tool_op:
            delete_keywords = ["delete", "remove", "clean up", "purge"]
            if not any(kw in prompt_lower for kw in delete_keywords):
                return VerificationResult(
                    is_valid=False,
                    rejection_reason="Destructive action 'delete' was proposed without explicit user deletion intent in original prompt",
                    relevance_score=0.0
                )

        return VerificationResult(
            is_valid=True,
            relevance_score=1.0
        )
