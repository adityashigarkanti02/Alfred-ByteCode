"""
Tests for Capability Manager and Cryptographic HMAC Signatures.

Verifies:
1. HMAC signature generation and verification.
2. Short expiration validity.
3. Parameter mutation defense (tampering tool, operation, scope, or destination).
4. Immediate revocation mechanism.
"""

from datetime import datetime, timedelta
import pytest
from backend.app.security.capability_manager.manager import CapabilityManager, CapabilityPayload


@pytest.fixture
def manager():
    return CapabilityManager()


def test_capability_generation_and_valid_use(manager):
    """Verifies that a newly issued capability is cryptographically valid."""
    cap = manager.issue_capability(
        user_id="user_123",
        task_id="task_abc",
        authorized_tool="companion_fs",
        exact_operation="write_file",
        resource_scope="documents/report.txt",
        permitted_destination=None,
        duration_seconds=300
    )

    is_valid, reason = manager.validate_capability(
        capability=cap,
        task_id="task_abc",
        tool_name="companion_fs",
        operation="write_file",
        target_resource="documents/report.txt"
    )
    assert is_valid is True
    assert "valid" in reason.lower()


def test_capability_parameter_tampering(manager):
    """Verifies that modifying capability properties fails HMAC check."""
    cap = manager.issue_capability(
        user_id="user_123",
        task_id="task_abc",
        authorized_tool="companion_fs",
        exact_operation="read_file",
        resource_scope="documents/safe.txt"
    )

    # Attempt to use capability on a different file
    is_valid, reason = manager.validate_capability(
        capability=cap,
        task_id="task_abc",
        tool_name="companion_fs",
        operation="read_file",
        target_resource="documents/other_secret.txt"
    )
    assert is_valid is False
    assert "scope violation" in reason.lower()


def test_capability_signature_tampering(manager):
    """Verifies that tampering with the signature itself fails verification."""
    cap = manager.issue_capability(
        user_id="user_123",
        task_id="task_abc",
        authorized_tool="gmail",
        exact_operation="read_email",
        resource_scope="msg_1"
    )
    # Corrupt signature
    cap.integrity_signature = "0000000000000000000000000000000000000000000000000000000000000000"

    is_valid, reason = manager.validate_capability(
        capability=cap,
        task_id="task_abc",
        tool_name="gmail",
        operation="read_email",
        target_resource="msg_1"
    )
    assert is_valid is False
    assert "signature verification failed" in reason.lower()


def test_capability_expiration(manager):
    """Verifies that expired capabilities are rejected."""
    cap = CapabilityPayload(
        capability_id="expired_1",
        user_id="user_123",
        task_id="task_abc",
        authorized_tool="gmail",
        exact_operation="read_email",
        resource_scope="*",
        expiration=datetime.utcnow() - timedelta(seconds=10)
    )
    cap.integrity_signature = manager._compute_digest(cap)

    is_valid, reason = manager.validate_capability(
        capability=cap,
        task_id="task_abc",
        tool_name="gmail",
        operation="read_email",
        target_resource="*"
    )
    assert is_valid is False
    assert "expired" in reason.lower()


def test_capability_revocation(manager):
    """Verifies that revoked capabilities are rejected immediately."""
    cap = manager.issue_capability(
        user_id="user_123",
        task_id="task_abc",
        authorized_tool="browser",
        exact_operation="navigate",
        resource_scope="*"
    )
    # Revoke
    manager.revoke_capability(cap.capability_id)

    is_valid, reason = manager.validate_capability(
        capability=cap,
        task_id="task_abc",
        tool_name="browser",
        operation="navigate",
        target_resource="*"
    )
    assert is_valid is False
    assert "revoked" in reason.lower()
