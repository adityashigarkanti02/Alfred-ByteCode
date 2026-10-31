"""
SQLAlchemy database models for ALFRED AI.

This module declares the relational data models supporting:
- Core identity and settings (Users, Integrations)
- Autonomous agent task lifecycles (Tasks, TaskSteps, ExecutionStates, ToolCalls)
- Dynamic Authority and Capability-based security (Capabilities, Approvals, SecurityDecisions, Policies)
- Information-Flow, Provenance, and Threat Auditing (Provenance, SecurityEvents, AuditLogs)
- Specialized Activity Auditing (FileOperations, EmailActivity)

Every model includes timestamps, foreign keys with referential integrity,
and field-level documentation describing security boundaries.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from backend.app.database.connection import Base


def generate_uuid() -> str:
    """Generate a standard UUID4 string for primary keys."""
    return str(uuid.uuid4())


class User(Base):
    """
    Represents an authenticated system operator or user.
    All tasks, capabilities, and audit trails tie back to a user principal.
    """
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)
    role = Column(String(50), default="OPERATOR")  # ADMIN, OPERATOR, VIEWER
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    capabilities = relationship("Capability", back_populates="user", cascade="all, delete-orphan")


class Integration(Base):
    """
    Manages credentials, connection status, and authorization boundaries for external services.
    Supports Gmail OAuth, Local Companion, and Web Browser Automation.
    """
    __tablename__ = "integrations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    service_name = Column(String(50), nullable=False, index=True)  # GMAIL, LOCAL_COMPANION, BROWSER
    is_connected = Column(Boolean, default=False)
    status_message = Column(String(255), nullable=True)
    # Encrypted settings or metadata (never plaintext secrets)
    config_json = Column(JSON, default=dict)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Task(Base):
    """
    Represents an autonomous user task submitted through natural language.
    Tracks overall execution state, security constraints, and final resolution.
    """
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    natural_language_prompt = Column(Text, nullable=False)
    
    # Task status: PENDING, PLANNING, EXECUTING, AWAITING_APPROVAL, COMPLETED, FAILED, CANCELLED, BLOCKED_ATTACK
    status = Column(String(50), default="PENDING", index=True)
    
    # Inferred and verified task scope (e.g. read email, summarize, send draft)
    declared_scope = Column(JSON, default=list)
    risk_level = Column(String(20), default="L0")  # L0, L1, L2, L3
    circuit_breaker_triggered = Column(Boolean, default=False)
    final_report = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="tasks")
    steps = relationship("TaskStep", back_populates="task", cascade="all, delete-orphan")
    tool_calls = relationship("ToolCall", back_populates="task", cascade="all, delete-orphan")
    security_decisions = relationship("SecurityDecision", back_populates="task", cascade="all, delete-orphan")
    capabilities = relationship("Capability", back_populates="task", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="task", cascade="all, delete-orphan")
    security_events = relationship("SecurityEvent", back_populates="task", cascade="all, delete-orphan")
    provenance_records = relationship("ProvenanceRecord", back_populates="task", cascade="all, delete-orphan")
    file_operations = relationship("FileOperation", back_populates="task", cascade="all, delete-orphan")
    email_activities = relationship("EmailActivity", back_populates="task", cascade="all, delete-orphan")


class TaskStep(Base):
    """
    Granular decomposed step within a task plan generated by the LLM planner.
    Cannot execute directly; each step must be translated to a validated ToolCall.
    """
    __tablename__ = "task_steps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    target_tool = Column(String(100), nullable=True)
    planned_operation = Column(String(100), nullable=True)
    status = Column(String(50), default="PENDING")  # PENDING, IN_PROGRESS, COMPLETED, FAILED, SKIPPED
    result_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="steps")


class ToolCall(Base):
    """
    Every operation proposal by the agent to access a tool/resource.
    Must pass through the Security Gateway and Dynamic Authority Engine before execution.
    """
    __tablename__ = "tool_calls"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    tool_name = Column(String(100), nullable=False)  # gmail, browser, companion_fs, etc.
    operation = Column(String(100), nullable=False)  # read_email, send_email, read_file, etc.
    arguments = Column(JSON, default=dict)
    
    # Status: PROPOSED, VERIFYING, APPROVED, REJECTED, EXECUTED, FAILED
    status = Column(String(50), default="PROPOSED", index=True)
    
    # Linked capability ID if authorized
    capability_id = Column(String(36), nullable=True)
    execution_result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    risk_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="tool_calls")


class SecurityDecision(Base):
    """
    Deterministic record of the security engine's ruling on a tool proposal.
    Provides verifiable proof of whether an operation was ALLOWED, DENIED, or requires APPROVAL.
    """
    __tablename__ = "security_decisions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    tool_call_id = Column(String(36), nullable=True, index=True)
    
    authority_level = Column(String(10), nullable=False)  # L0, L1, L2, L3
    decision = Column(String(30), nullable=False)  # ALLOW, REQUIRE_APPROVAL, DENY
    policy_rule = Column(String(200), nullable=False)
    rationale = Column(Text, nullable=False)
    
    taint_detected = Column(Boolean, default=False)
    prompt_injection_detected = Column(Boolean, default=False)
    
    timestamp = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="security_decisions")


class Capability(Base):
    """
    Cryptographically verifiable, short-lived authorization token granting
    the agent permission for one EXACT action within a bounded resource scope.
    """
    __tablename__ = "capabilities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    
    authorized_tool = Column(String(100), nullable=False)
    exact_operation = Column(String(100), nullable=False)
    resource_scope = Column(String(500), nullable=False)  # e.g., canonical folder path or email ID
    permitted_destination = Column(String(500), nullable=True)  # e.g., recipient email or output path
    
    # Cryptographic integrity signature (HMAC-SHA256)
    integrity_signature = Column(String(128), nullable=False)
    
    expiration = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="capabilities")
    task = relationship("Task", back_populates="capabilities")


class Approval(Base):
    """
    A pending or resolved human authorization request for sensitive L2 operations.
    Strictly bound to exact immutable parameters.
    """
    __tablename__ = "approvals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    capability_id = Column(String(36), nullable=True)
    
    tool_name = Column(String(100), nullable=False)
    operation = Column(String(100), nullable=False)
    parameters = Column(JSON, nullable=False)  # Immutable snapshot of requested parameters
    explanation = Column(Text, nullable=False)
    
    # Status: PENDING, APPROVED, REJECTED, EXPIRED
    status = Column(String(30), default="PENDING", index=True)
    decided_by = Column(String(255), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="approvals")


class SecurityEvent(Base):
    """
    Logged whenever prompt injection, untrusted control flow, or unauthorized access is intercepted.
    Feed into dashboard and threat intelligence metrics.
    """
    __tablename__ = "security_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=True, index=True)
    
    threat_category = Column(String(100), nullable=False)  # DIRECT_INJECTION, HIDDEN_TEXT, TAINT_ESCALATION, etc.
    risk_score = Column(Float, nullable=False)  # 0.0 to 1.0
    source = Column(String(100), nullable=False)  # EMAIL_BODY, PDF_ATTACHMENT, WEB_HTML, etc.
    source_location = Column(String(255), nullable=True)
    explanation = Column(Text, nullable=False)
    suspicious_excerpt = Column(Text, nullable=True)
    action_taken = Column(String(50), default="BLOCKED")  # BLOCKED, SANITIZED, FLAGGED
    
    timestamp = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="security_events")


class ProvenanceRecord(Base):
    """
    Tracks origin and taint label for every piece of data ingested into context.
    Prevents untrusted external content from directing downstream actions.
    """
    __tablename__ = "provenance_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    data_hash = Column(String(64), nullable=False, index=True)
    
    # Trust label: TRUSTED_POLICY, USER_AUTHORIZED, UNTRUSTED_EXTERNAL, UNTRUSTED_PROPOSAL, AUTHORIZED_FOR_EXACT_SCOPE
    trust_label = Column(String(50), nullable=False)
    origin_source = Column(String(255), nullable=False)  # e.g., 'gmail:msg_123', 'web:https://...'
    content_snippet = Column(Text, nullable=True)
    is_tainted = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="provenance_records")


class FileOperation(Base):
    """
    Audit log of every filesystem access attempted via Local Companion.
    Maintains canonical path boundaries and verifies capability linkage.
    """
    __tablename__ = "file_operations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=True, index=True)
    
    # READ, WRITE, EDIT, RENAME, MOVE, DELETE, SEARCH
    operation_type = Column(String(50), nullable=False)
    canonical_path = Column(Text, nullable=False)
    destination_path = Column(Text, nullable=True)
    is_successful = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    capability_id = Column(String(36), nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="file_operations")


class EmailActivity(Base):
    """
    Comprehensive log of email interactions via Gmail integration.
    Captures inbound extraction and outbound authorized sending.
    """
    __tablename__ = "email_activities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=True, index=True)
    
    direction = Column(String(20), nullable=False)  # INBOUND, OUTBOUND, DRAFT
    message_id = Column(String(255), nullable=True)
    thread_id = Column(String(255), nullable=True)
    sender = Column(String(255), nullable=True)
    recipients = Column(JSON, default=list)
    subject = Column(String(500), nullable=True)
    snippet = Column(Text, nullable=True)
    has_attachments = Column(Boolean, default=False)
    is_suspicious = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="email_activities")


class AuditLog(Base):
    """
    Tamper-evident audit trail for all system operations, authorization checks,
    and state transitions across ALFRED AI.
    """
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), nullable=True, index=True)
    actor = Column(String(50), nullable=False)  # USER, PLANNER, SECURITY_GATEWAY, COMPANION, GMAIL
    action = Column(String(100), nullable=False)
    details = Column(JSON, default=dict)
    status = Column(String(50), default="SUCCESS")
    integrity_hash = Column(String(64), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class Policy(Base):
    """
    Configurable deterministic security rule defining authority levels and constraints.
    """
    __tablename__ = "policies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=False)
    authority_level = Column(String(10), nullable=False)  # L0, L1, L2, L3
    tool_pattern = Column(String(100), nullable=False)  # e.g., 'gmail:send_email' or 'companion_fs:delete'
    requires_approval = Column(Boolean, default=False)
    is_hard_deny = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
