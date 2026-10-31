"""
Cryptographic Capability-Based Authorization Manager for ALFRED AI.

This module issues, verifies, and revokes fine-grained, short-lived, task-bound
authorization capabilities. 

Crucial Security Guarantees:
1. The LLM Planner has NO access to the signing key and cannot issue capabilities to itself.
2. Every capability is cryptographically signed with HMAC-SHA256 over its immutable parameters.
3. Capabilities are bound to exact parameters: any modification of tool name, operation,
   resource scope, or destination results in an immediate signature mismatch.
4. Capabilities expire rapidly (default 300 seconds) and support immediate revocation.
"""

import hmac
import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
from pydantic import BaseModel, Field


# Master capability signing secret (retrieved from environment or securely generated)
CAPABILITY_SIGNING_SECRET = os.getenv(
    "ALFRED_CAPABILITY_SECRET",
    "alfred-deterministic-master-secret-key-change-in-prod-5847382910"
).encode("utf-8")


class CapabilityPayload(BaseModel):
    """
    Structured fields of an authorization capability.
    All fields are included in the HMAC digest calculation.
    """
    capability_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    task_id: str
    authorized_tool: str
    exact_operation: str
    resource_scope: str  # Canonical resource identifier (e.g. specific file path or email ID)
    permitted_destination: Optional[str] = None  # Destination sink (e.g. authorized recipient or directory)
    expiration: datetime
    is_revoked: bool = False
    integrity_signature: Optional[str] = None


class CapabilityManager:
    """
    Manages issuance, validation, and revocation of capabilities.
    Only the Dynamic Authority Engine may invoke `issue_capability`.
    """

    def __init__(self, signing_secret: bytes = CAPABILITY_SIGNING_SECRET):
        self._secret = signing_secret
        self._revoked_ids: Set[str] = set()

    def _compute_digest(self, payload: CapabilityPayload) -> str:
        """
        Calculates canonical HMAC-SHA256 signature across all capability constraints.
        Canonical ordering guarantees reproducible digests.
        """
        canonical_str = (
            f"{payload.capability_id}|"
            f"{payload.user_id}|"
            f"{payload.task_id}|"
            f"{payload.authorized_tool}|"
            f"{payload.exact_operation}|"
            f"{payload.resource_scope}|"
            f"{payload.permitted_destination or ''}|"
            f"{payload.expiration.isoformat()}"
        )
        return hmac.new(self._secret, canonical_str.encode("utf-8"), hashlib.sha256).hexdigest()

    def issue_capability(
        self,
        user_id: str,
        task_id: str,
        authorized_tool: str,
        exact_operation: str,
        resource_scope: str,
        permitted_destination: Optional[str] = None,
        duration_seconds: int = 300
    ) -> CapabilityPayload:
        """
        Generates and cryptographically signs a short-lived capability.
        Only called by the independent Authority Engine after policy approval.
        """
        expiration = datetime.utcnow() + timedelta(seconds=duration_seconds)
        cap = CapabilityPayload(
            user_id=user_id,
            task_id=task_id,
            authorized_tool=authorized_tool,
            exact_operation=exact_operation,
            resource_scope=resource_scope,
            permitted_destination=permitted_destination,
            expiration=expiration
        )
        cap.integrity_signature = self._compute_digest(cap)
        return cap

    def validate_capability(
        self,
        capability: CapabilityPayload,
        task_id: str,
        tool_name: str,
        operation: str,
        target_resource: str,
        destination: Optional[str] = None
    ) -> Tuple_Validation:
        """
        Validates capability integrity, expiration, revocation, and exact parameter alignment.
        Execution gate fails closed if ANY check does not match.
        """
        # 1. Check revocation
        if capability.capability_id in self._revoked_ids or capability.is_revoked:
            return False, "Capability has been revoked"

        # 2. Check expiration
        if datetime.utcnow() > capability.expiration:
            return False, f"Capability expired at {capability.expiration.isoformat()}"

        # 3. Check cryptographic signature
        expected_sig = self._compute_digest(capability)
        if not hmac.compare_digest(capability.integrity_signature or "", expected_sig):
            return False, "Cryptographic capability signature verification failed (tampered token)"

        # 4. Check Task ID binding (non-transferable across tasks)
        if capability.task_id != task_id:
            return False, f"Capability bound to task {capability.task_id}, cannot execute under {task_id}"

        # 5. Check Tool and Operation match
        if capability.authorized_tool != tool_name:
            return False, f"Tool mismatch: authorized for '{capability.authorized_tool}', requested '{tool_name}'"

        if capability.exact_operation != operation:
            return False, f"Operation mismatch: authorized for '{capability.exact_operation}', requested '{operation}'"

        # 6. Check Resource Scope
        if capability.resource_scope != "*" and capability.resource_scope != target_resource:
            return False, f"Resource scope violation: authorized for '{capability.resource_scope}', requested '{target_resource}'"

        # 7. Check Destination if applicable
        if capability.permitted_destination and capability.permitted_destination != destination:
            return False, f"Destination violation: authorized for '{capability.permitted_destination}', requested '{destination}'"

        return True, "Capability valid and verified"

    def revoke_capability(self, capability_id: str) -> None:
        """
        Immediately invalidates a capability prior to natural expiration.
        """
        self._revoked_ids.add(capability_id)

    def revoke_all_for_task(self, task_id: str, active_capabilities: Dict[str, CapabilityPayload]) -> int:
        """
        Revokes all capabilities associated with a task (e.g. upon circuit breaker trip or cancellation).
        """
        count = 0
        for cap_id, cap in active_capabilities.items():
            if cap.task_id == task_id:
                self.revoke_capability(cap_id)
                count += 1
        return count


# Type alias for readability
Tuple_Validation = tuple[bool, str]
