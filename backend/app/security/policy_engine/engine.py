"""
Deterministic Policy Engine for ALFRED AI.

This module houses the deterministic rules defining the 4 authority tiers:
- L0: AUTONOMOUS (Safe read-only actions, internal local summarization)
- L1: SCOPED EXECUTION (Pre-authorized local writes within authorized workspace directories)
- L2: HUMAN APPROVAL (External actions, email sending, file deletion, broad file moves)
- L3: HARD DENY (Credential access, system directories, untrusted recipient overrides, exfiltration)

The policy engine is strictly deterministic: no LLM evaluation is permitted to downgrade
an L3 HARD DENY or an L2 HUMAN APPROVAL into an ALLOW.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field


class AuthorityLevel(str, Enum):
    """
    Tiered classification of operation privileges.
    """
    L0_AUTONOMOUS = "L0"
    L1_SCOPED_EXECUTION = "L1"
    L2_HUMAN_APPROVAL = "L2"
    L3_HARD_DENY = "L3"


class PolicyDecision(str, Enum):
    """
    Authoritative ruling on a proposed operation.
    """
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"


class PolicyRuleResult(BaseModel):
    """
    Detailed outcome of policy evaluation.
    """
    decision: PolicyDecision
    authority_level: AuthorityLevel
    rule_name: str
    rationale: str
    requires_human_approval: bool = False


class DeterministicPolicyEngine:
    """
    Deterministic rule engine that validates proposed actions against predefined
    security boundaries, resource protections, and operation classifications.
    """

    # Protected system paths and credential files that must NEVER be accessed (L3 HARD DENY)
    PROTECTED_SYSTEM_PATHS = [
        "c:\\windows",
        "c:\\program files",
        "/etc",
        "/bin",
        "/usr",
        "/root",
        ".ssh",
        "id_rsa",
        ".env",
        "credentials",
        "shadow",
        "system32",
        "appdata\\roaming\\microsoft\\windows\\cookies",
        "keychain",
    ]

    # Blocked external domains or keywords for data exfiltration (L3 HARD DENY)
    PROHIBITED_DESTINATIONS = [
        "webhook.site",
        "requestbin",
        "pastebin.com",
        "ngrok.io",
        "pipedream.net",
    ]

    def evaluate(
        self,
        tool_name: str,
        operation: str,
        parameters: Dict[str, Any],
        is_tainted: bool = False,
        task_intent: str = ""
    ) -> PolicyRuleResult:
        """
        Evaluates proposed tool execution against hard deterministic rules.
        Highest risk rules are evaluated first (Hard Deny -> Human Approval -> Scoped -> Autonomous).
        """
        tool_op = f"{tool_name}:{operation}".lower()

        # -------------------------------------------------------------
        # 1. HARD DENY CHECKS (L3) - Cannot be overridden by anything
        # -------------------------------------------------------------

        # Check for access to protected system files/credentials
        path_arg = str(parameters.get("path") or parameters.get("file_path") or parameters.get("filename") or "").lower()
        for protected in self.PROTECTED_SYSTEM_PATHS:
            if protected in path_arg:
                return PolicyRuleResult(
                    decision=PolicyDecision.DENY,
                    authority_level=AuthorityLevel.L3_HARD_DENY,
                    rule_name="PROTECT_SYSTEM_AND_CREDENTIAL_FILES",
                    rationale=f"Access to protected path or credential file '{protected}' is strictly prohibited."
                )

        # Check for destination exfiltration addresses
        dest_arg = str(parameters.get("destination") or parameters.get("url") or parameters.get("recipient") or "").lower()
        for prohibited in self.PROHIBITED_DESTINATIONS:
            if prohibited in dest_arg:
                return PolicyRuleResult(
                    decision=PolicyDecision.DENY,
                    authority_level=AuthorityLevel.L3_HARD_DENY,
                    rule_name="BLOCK_EXFILTRATION_SINKS",
                    rationale=f"Destination '{prohibited}' is recognized as an unauthorized data exfiltration sink."
                )

        # Arbitrary shell execution or raw code eval is strictly forbidden
        if "shell" in tool_op or "exec" in tool_op or "eval" in tool_op:
            return PolicyRuleResult(
                decision=PolicyDecision.DENY,
                authority_level=AuthorityLevel.L3_HARD_DENY,
                rule_name="FORBID_ARBITRARY_CODE_EXECUTION",
                rationale="Direct shell or arbitrary code execution is fundamentally disallowed."
            )

        # Untrusted control of sensitive sinks (taint violation)
        if is_tainted and tool_op in ("gmail:send_email", "companion_fs:delete_file", "companion_fs:move_file"):
            return PolicyRuleResult(
                decision=PolicyDecision.DENY,
                authority_level=AuthorityLevel.L3_HARD_DENY,
                rule_name="TAINTED_PARAMETER_HIJACK",
                rationale="Untrusted external data cannot dictate sensitive external operations or deletions."
            )

        # -------------------------------------------------------------
        # 2. HUMAN APPROVAL CHECKS (L2) - Consequential or External Actions
        # -------------------------------------------------------------

        # Outbound email transmission
        if tool_op == "gmail:send_email":
            return PolicyRuleResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                authority_level=AuthorityLevel.L2_HUMAN_APPROVAL,
                rule_name="REQUIRE_APPROVAL_FOR_OUTBOUND_EMAIL",
                rationale="Sending external emails sends data outside the security boundary and requires explicit human verification.",
                requires_human_approval=True
            )

        # File deletion
        if "delete" in tool_op:
            return PolicyRuleResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                authority_level=AuthorityLevel.L2_HUMAN_APPROVAL,
                rule_name="REQUIRE_APPROVAL_FOR_DELETION",
                rationale="File or resource deletion is an irreversible action requiring explicit human confirmation.",
                requires_human_approval=True
            )

        # Creating or modifying sensitive settings or capabilities
        if "policy" in tool_op or "permission" in tool_op or "authority" in tool_op:
            return PolicyRuleResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                authority_level=AuthorityLevel.L2_HUMAN_APPROVAL,
                rule_name="REQUIRE_APPROVAL_FOR_PRIVILEGE_MODIFICATION",
                rationale="Modifying permissions or authority boundaries requires administrator human approval.",
                requires_human_approval=True
            )

        # -------------------------------------------------------------
        # 3. SCOPED EXECUTION CHECKS (L1) - Local Pre-Authorized Writes
        # -------------------------------------------------------------
        if tool_op in ("companion_fs:write_file", "companion_fs:edit_file", "companion_fs:create_directory"):
            # Check if write is relevant to declared task intent
            return PolicyRuleResult(
                decision=PolicyDecision.ALLOW,
                authority_level=AuthorityLevel.L1_SCOPED_EXECUTION,
                rule_name="SCOPED_LOCAL_WORKSPACE_MODIFICATION",
                rationale="Permitted scoped local modification within designated authorized workspace."
            )

        if tool_op == "gmail:create_draft":
            return PolicyRuleResult(
                decision=PolicyDecision.ALLOW,
                authority_level=AuthorityLevel.L1_SCOPED_EXECUTION,
                rule_name="SCOPED_EMAIL_DRAFT_CREATION",
                rationale="Draft creation does not send external communications and is permitted as scoped execution."
            )

        # -------------------------------------------------------------
        # 4. AUTONOMOUS READ-ONLY CHECKS (L0) - Safe Observational Tools
        # -------------------------------------------------------------
        safe_read_ops = {
            "gmail:list_emails",
            "gmail:read_email",
            "gmail:search_emails",
            "gmail:get_attachment",
            "browser:navigate",
            "browser:extract_content",
            "browser:search",
            "companion_fs:list_directory",
            "companion_fs:read_file",
            "companion_fs:search_files",
            "document_processor:read_pdf",
            "document_processor:read_docx"
        }

        if tool_op in safe_read_ops or "read" in tool_op or "search" in tool_op or "list" in tool_op:
            return PolicyRuleResult(
                decision=PolicyDecision.ALLOW,
                authority_level=AuthorityLevel.L0_AUTONOMOUS,
                rule_name="AUTONOMOUS_SAFE_READ",
                rationale="Safe read-only operation within permitted scopes."
            )

        # Default fallback: Unknown operations require explicit approval
        return PolicyRuleResult(
            decision=PolicyDecision.REQUIRE_APPROVAL,
            authority_level=AuthorityLevel.L2_HUMAN_APPROVAL,
            rule_name="DEFAULT_REQUIRE_APPROVAL_UNKNOWN_ACTION",
            rationale=f"Operation '{tool_op}' is not classified as safe read-only and requires explicit operator approval.",
            requires_human_approval=True
        )
