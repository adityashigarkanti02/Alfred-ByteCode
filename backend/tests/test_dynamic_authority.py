"""
Tests for Dynamic Authority Engine and Deterministic Policies.

Verifies:
1. Authority level classifications (L0, L1, L2, L3).
2. Dynamic policy checks on varied actions.
3. Emergency Circuit Breaker trigger upon repeated violations.
4. Circuit breaker reset.
"""

import pytest
from backend.app.security.authority_engine.engine import DynamicAuthorityEngine
from backend.app.security.policy_engine.engine import DeterministicPolicyEngine, PolicyDecision, AuthorityLevel
from backend.app.security.capability_manager.manager import CapabilityManager


@pytest.fixture
def authority_engine():
    return DynamicAuthorityEngine(
        policy_engine=DeterministicPolicyEngine(),
        capability_manager=CapabilityManager(),
        circuit_breaker_threshold=2
    )


def test_l0_autonomous_safe_read(authority_engine):
    """Verifies that reading an email or directory is allowed as L0."""
    res = authority_engine.evaluate_proposal(
        user_id="u1",
        task_id="t1",
        tool_name="gmail",
        operation="read_email",
        parameters={"message_id": "msg_123"},
        task_intent="Read my emails"
    )
    assert res.decision == PolicyDecision.ALLOW
    assert res.authority_level == AuthorityLevel.L0_AUTONOMOUS
    assert res.capability is not None


def test_l2_human_approval_for_email_sending(authority_engine):
    """Verifies that sending email requires human approval (L2)."""
    res = authority_engine.evaluate_proposal(
        user_id="u1",
        task_id="t1",
        tool_name="gmail",
        operation="send_email",
        parameters={"to_recipients": ["someone@example.com"], "subject": "Test", "body": "Body"},
        task_intent="Send email"
    )
    assert res.decision == PolicyDecision.REQUIRE_APPROVAL
    assert res.authority_level == AuthorityLevel.L2_HUMAN_APPROVAL
    assert res.capability is None


def test_l3_hard_deny_on_system_path(authority_engine):
    """Verifies that accessing protected system folders triggers L3 Hard Deny."""
    res = authority_engine.evaluate_proposal(
        user_id="u1",
        task_id="t1",
        tool_name="companion_fs",
        operation="read_file",
        parameters={"path": "C:\\Windows\\System32\\cmd.exe"},
        task_intent="Check files"
    )
    assert res.decision == PolicyDecision.DENY
    assert res.authority_level == AuthorityLevel.L3_HARD_DENY


def test_circuit_breaker_tripping(authority_engine):
    """Verifies that consecutive violations trip the circuit breaker."""
    # First violation
    r1 = authority_engine.evaluate_proposal(
        user_id="u1",
        task_id="t_breaker",
        tool_name="companion_fs",
        operation="read_file",
        parameters={"path": "/etc/shadow"},
        task_intent="Malicious task"
    )
    assert r1.decision == PolicyDecision.DENY
    assert r1.circuit_breaker_tripped is False

    # Second violation -> reaches threshold of 2
    r2 = authority_engine.evaluate_proposal(
        user_id="u1",
        task_id="t_breaker",
        tool_name="companion_fs",
        operation="read_file",
        parameters={"path": "C:\\Windows\\secrets.txt"},
        task_intent="Malicious task"
    )
    assert r2.decision == PolicyDecision.DENY
    assert r2.circuit_breaker_tripped is True
    assert authority_engine.is_circuit_breaker_tripped("t_breaker") is True

    # Subsequent safe operation is also blocked due to active circuit breaker
    r3 = authority_engine.evaluate_proposal(
        user_id="u1",
        task_id="t_breaker",
        tool_name="gmail",
        operation="read_email",
        parameters={"message_id": "msg_safe"},
        task_intent="Safe read"
    )
    assert r3.decision == PolicyDecision.DENY
    assert r3.circuit_breaker_tripped is True

    # Reset circuit breaker
    authority_engine.reset_circuit_breaker("t_breaker")
    assert authority_engine.is_circuit_breaker_tripped("t_breaker") is False
