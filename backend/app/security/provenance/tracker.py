"""
Information-Flow Provenance Tracker for ALFRED AI.

This module implements taint-tracking and data provenance metadata. Every piece of
data ingested by the agent (user instructions, emails, PDFs, webpage DOMs, local files)
is wrapped in a TaintedString or ProvenanceEnvelope stamped with a trust label:

- TRUSTED_POLICY: Hardcoded system policies and security constraints.
- USER_AUTHORIZED: The user's direct prompts, settings, and explicit UI approvals.
- UNTRUSTED_EXTERNAL: Ingested content from emails, web pages, PDFs, and third parties.
- UNTRUSTED_PROPOSAL: LLM-generated tool call proposals before security validation.
- AUTHORIZED_FOR_EXACT_SCOPE: Sanitized or vetted content explicitly cleared for a single sink.

Untrusted data cannot flow directly into sensitive control sinks (such as email
recipients, external URLs, file paths, or shell arguments) without triggering
security policy violations.
"""

import hashlib
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TrustLabel(str, Enum):
    """
    Standard hierarchical trust classifications.
    Higher privilege labels cannot be synthesized from lower privilege data.
    """
    TRUSTED_POLICY = "TRUSTED_POLICY"
    USER_AUTHORIZED = "USER_AUTHORIZED"
    UNTRUSTED_EXTERNAL = "UNTRUSTED_EXTERNAL"
    UNTRUSTED_PROPOSAL = "UNTRUSTED_PROPOSAL"
    AUTHORIZED_FOR_EXACT_SCOPE = "AUTHORIZED_FOR_EXACT_SCOPE"


class ProvenanceEnvelope(BaseModel):
    """
    Metadata container that travels with all ingested and transformed data.
    Maintains a verifiable trail of origins, taint markers, and transformation steps.
    """
    content: str = Field(description="The actual text content or payload")
    trust_label: TrustLabel = Field(description="The provenance trust classification")
    origin_source: str = Field(description="Identifier of origin, e.g. 'gmail:msg_8849', 'user:prompt'")
    content_hash: str = Field(description="SHA-256 fingerprint of the original raw content")
    is_tainted: bool = Field(description="True if originated from or influenced by an untrusted source")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context such as mime-type or sender")

    @classmethod
    def create(
        cls,
        content: str,
        trust_label: TrustLabel,
        origin_source: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "ProvenanceEnvelope":
        """
        Factory method to initialize a provenance envelope with automatic hash calculation
        and taint status determination.
        """
        raw_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        is_tainted = trust_label in (TrustLabel.UNTRUSTED_EXTERNAL, TrustLabel.UNTRUSTED_PROPOSAL)
        return cls(
            content=content,
            trust_label=trust_label,
            origin_source=origin_source,
            content_hash=raw_hash,
            is_tainted=is_tainted,
            metadata=metadata or {}
        )


class ProvenanceTracker:
    """
    In-memory registry and validator for tracking active provenance envelopes per task.
    Enforces that derived data maintains taint flags of parent inputs.
    """

    def __init__(self):
        # Map of content_hash -> ProvenanceEnvelope
        self._registry: Dict[str, ProvenanceEnvelope] = {}

    def register(self, envelope: ProvenanceEnvelope) -> None:
        """
        Registers an envelope in the provenance store.
        """
        self._registry[envelope.content_hash] = envelope

    def get_by_hash(self, content_hash: str) -> Optional[ProvenanceEnvelope]:
        """
        Retrieves provenance metadata by data hash.
        """
        return self._registry.get(content_hash)

    def derive(
        self,
        new_content: str,
        parent_envelopes: List[ProvenanceEnvelope],
        operation_name: str
    ) -> ProvenanceEnvelope:
        """
        Derives a new envelope from parent envelopes. If ANY parent is tainted,
        the derived output is automatically tainted.
        """
        is_tainted = any(p.is_tainted for p in parent_envelopes)
        
        # If any parent is untrusted external, the output remains untrusted external
        if any(p.trust_label == TrustLabel.UNTRUSTED_EXTERNAL for p in parent_envelopes):
            label = TrustLabel.UNTRUSTED_EXTERNAL
        elif any(p.trust_label == TrustLabel.UNTRUSTED_PROPOSAL for p in parent_envelopes):
            label = TrustLabel.UNTRUSTED_PROPOSAL
        elif all(p.trust_label == TrustLabel.USER_AUTHORIZED for p in parent_envelopes):
            label = TrustLabel.USER_AUTHORIZED
        else:
            label = TrustLabel.UNTRUSTED_EXTERNAL

        sources = [p.origin_source for p in parent_envelopes]
        envelope = ProvenanceEnvelope.create(
            content=new_content,
            trust_label=label,
            origin_source=f"derived:{operation_name}[{','.join(sources)}]",
            metadata={"operation": operation_name, "parent_hashes": [p.content_hash for p in parent_envelopes]}
        )
        self.register(envelope)
        return envelope

    def check_flow_permitted(
        self,
        source_envelope: ProvenanceEnvelope,
        destination_sink: str
    ) -> bool:
        """
        Evaluates whether information in source_envelope is permitted to flow
        into destination_sink.
        
        Forbidden flows:
        - UNTRUSTED_EXTERNAL -> SENSITIVE_CONTROL_SINKS (e.g., 'email_recipient', 'cmd_exec', 'file_destination')
        """
        sensitive_sinks = {
            "email_recipient",
            "file_destination_path",
            "shell_command",
            "authorization_grant",
            "policy_override",
            "network_destination_host"
        }

        if destination_sink in sensitive_sinks and source_envelope.is_tainted:
            return False

        return True
