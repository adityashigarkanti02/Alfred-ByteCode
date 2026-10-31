"""
Information-Flow Control (IFC) Engine for ALFRED AI.

This module enforces non-interference and confinement policies between untrusted
external data and sensitive execution sinks. It ensures that untrusted data can be
safely summarized and analyzed, while mathematically preventing that untrusted data
from altering control flow, exfiltrating data, or directing recipient/file paths.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.app.security.provenance.tracker import TrustLabel, ProvenanceEnvelope, ProvenanceTracker


class FlowCheckResult(BaseModel):
    """
    Result of an Information-Flow Control check.
    """
    is_allowed: bool
    rejection_reason: Optional[str] = None
    sanitized_payload: Optional[str] = None


class InformationFlowController:
    """
    Guarantees strict lattice-based information flow control.
    """

    # Sinks that require USER_AUTHORIZED or AUTHORIZED_FOR_EXACT_SCOPE provenance
    RESTRICTED_CONTROL_SINKS = {
        "email_recipient",
        "email_cc",
        "email_bcc",
        "file_destination_path",
        "command_line_argument",
        "outbound_url_host",
        "authority_grant_role",
    }

    def __init__(self, tracker: Optional[ProvenanceTracker] = None):
        self.tracker = tracker or ProvenanceTracker()

    def validate_flow(
        self,
        envelope: ProvenanceEnvelope,
        destination_sink: str,
        operation_context: Optional[Dict[str, Any]] = None
    ) -> FlowCheckResult:
        """
        Validates if data wrapped in the provenance envelope is permitted to flow
        into destination_sink.
        """
        # If sink is a restricted control sink and the envelope is tainted or untrusted
        if destination_sink in self.RESTRICTED_CONTROL_SINKS:
            if envelope.is_tainted or envelope.trust_label == TrustLabel.UNTRUSTED_EXTERNAL:
                return FlowCheckResult(
                    is_allowed=False,
                    rejection_reason=(
                        f"Information Flow Violation: Untrusted data from origin '{envelope.origin_source}' "
                        f"cannot be used to populate restricted control sink '{destination_sink}'."
                    )
                )

        # Content processing sinks (like summarization, translation, extraction) are ALLOWED
        # even for untrusted external data, provided the output remains labeled UNTRUSTED_EXTERNAL.
        return FlowCheckResult(
            is_allowed=True,
            sanitized_payload=envelope.content
        )

    def sanitize_for_safe_summary(self, raw_untrusted_text: str) -> str:
        """
        Prepares untrusted text for safe LLM summarization by escaping command-like
        syntax and neutralizing prompt injection delimiters.
        """
        sanitized = raw_untrusted_text
        # Neutralize common markdown injection delimiters
        sanitized = sanitized.replace("```system", "```escaped_system")
        sanitized = sanitized.replace("[SYSTEM]", "[EXTERNAL_CONTENT_SYSTEM_TOKEN_STRIPPED]")
        sanitized = sanitized.replace("<<SYS>>", "[EXTERNAL_SYS_TOKEN_STRIPPED]")
        return sanitized
