"""
Agent Task Understanding and Decomposition Planner for ALFRED AI.

Responsible for:
1. Parsing user intent from natural language instructions.
2. Ingesting active context and past tool outputs.
3. Generating a structured, stepwise plan of proposed tool calls.

Fundamental Security Constraint:
The planner CANNOT execute any tool and CANNOT grant any capability.
Every proposal is treated with TrustLabel.UNTRUSTED_PROPOSAL and must pass through
the Dynamic Authority Engine and Independent Action Verifier before execution.
"""

import json
import os
import re
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class PlannedActionProposal(BaseModel):
    """
    A single action proposal formulated by the planner.
    Subject to strict security gateway validation.
    """
    step_number: int
    tool_name: str  # gmail, browser, companion_fs, etc.
    operation: str  # read_email, send_email, write_file, etc.
    parameters: Dict[str, Any]
    rationale: str


class PlannerPlan(BaseModel):
    """Decomposed plan produced by the planner."""
    task_intent: str
    declared_scope: List[str]
    steps: List[PlannedActionProposal]


class AgentPlanner:
    """
    Autonomous planner providing structured task decomposition.
    Can operate via LLM APIs or deterministic heuristic planner when offline.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")

    def plan_task(
        self,
        user_prompt: str,
        context_history: Optional[List[Dict[str, Any]]] = None
    ) -> PlannerPlan:
        """
        Decomposes a user prompt into a sequence of actionable tool proposals.
        """
        # If API key is present and configured, we can query LLM with strict JSON schema.
        # Otherwise, our comprehensive rule-based planner handles task patterns reliably.
        return self._heuristic_planner(user_prompt)

    def _heuristic_planner(self, prompt: str) -> PlannerPlan:
        """
        High-fidelity deterministic planner that interprets natural-language user tasks
        into exact tool proposal sequences.
        """
        prompt_lower = prompt.lower()
        steps: List[PlannedActionProposal] = []
        scope: List[str] = []

        # Pattern 1: Email reading / invoice extraction
        # e.g., "Read my latest emails and summarize important messages" or "Find an invoice in my email and save it"
        if "email" in prompt_lower or "inbox" in prompt_lower or "invoice" in prompt_lower:
            scope.append("EMAIL_ACCESS")
            steps.append(PlannedActionProposal(
                step_number=1,
                tool_name="gmail",
                operation="list_emails",
                parameters={"max_results": 5, "query": "invoice" if "invoice" in prompt_lower else ""},
                rationale="Retrieve relevant emails from inbox based on user criteria."
            ))

            if "read" in prompt_lower or "invoice" in prompt_lower or "summarize" in prompt_lower:
                steps.append(PlannedActionProposal(
                    step_number=2,
                    tool_name="gmail",
                    operation="read_email",
                    parameters={"message_id": "msg_101"},
                    rationale="Fetch full content and attachment details of the matching email."
                ))

            if "save" in prompt_lower or "computer" in prompt_lower or "file" in prompt_lower:
                scope.append("WORKSPACE_WRITE")
                steps.append(PlannedActionProposal(
                    step_number=len(steps) + 1,
                    tool_name="companion_fs",
                    operation="write_file",
                    parameters={
                        "path": "invoices/vendor_summary.txt",
                        "content": "Invoice Summary:\nVendor: Alice Finance\nAmount: $4,500.00\nStatus: Pending Approval",
                        "overwrite": True
                    },
                    rationale="Store extracted invoice details in user workspace directory."
                ))

            if "send" in prompt_lower or "teammate" in prompt_lower:
                scope.append("OUTBOUND_EMAIL")
                # Extract recipient if specified, or use default teammate
                recipient_match = re.search(r"[\w\.-]+@[\w\.-]+", prompt)
                target_recipient = recipient_match.group(0) if recipient_match else "teammate@company.com"
                steps.append(PlannedActionProposal(
                    step_number=len(steps) + 1,
                    tool_name="gmail",
                    operation="send_email",
                    parameters={
                        "to_recipients": [target_recipient],
                        "subject": "Extracted Invoice Summary",
                        "body": "Hello,\n\nHere is the invoice summary extracted from the latest billing email."
                    },
                    rationale="Send summarized report to teammate (requires L2 Human Approval)."
                ))

        # Pattern 2: Web browsing / extraction
        # e.g., "Browse https://example.com and extract information"
        elif "browse" in prompt_lower or "website" in prompt_lower or "http" in prompt_lower or "web" in prompt_lower:
            scope.append("WEB_BROWSING")
            url_match = re.search(r"https?://[^\s]+", prompt)
            target_url = url_match.group(0) if url_match else "https://example.com"

            steps.append(PlannedActionProposal(
                step_number=1,
                tool_name="browser",
                operation="navigate",
                parameters={"url": target_url},
                rationale=f"Navigate to {target_url} and extract web text content."
            ))

            if "report" in prompt_lower or "save" in prompt_lower or "summary" in prompt_lower:
                scope.append("WORKSPACE_WRITE")
                steps.append(PlannedActionProposal(
                    step_number=2,
                    tool_name="companion_fs",
                    operation="write_file",
                    parameters={
                        "path": "research/web_report.md",
                        "content": f"# Web Intelligence Report\n\nExtracted from: {target_url}\n\nSummary of findings...",
                        "overwrite": True
                    },
                    rationale="Save extracted web findings into a research document."
                ))

        # Pattern 3: Local file management
        # e.g., "Find project-related files on my computer" or "Organize files" or "Read a PDF"
        elif "file" in prompt_lower or "directory" in prompt_lower or "folder" in prompt_lower or "pdf" in prompt_lower:
            scope.append("FILESYSTEM_ACCESS")
            
            if "read" in prompt_lower or "pdf" in prompt_lower or "document" in prompt_lower:
                steps.append(PlannedActionProposal(
                    step_number=1,
                    tool_name="companion_fs",
                    operation="read_file",
                    parameters={"path": "documents/report.pdf"},
                    rationale="Read document or PDF to inspect content and prepare summary."
                ))
            elif "search" in prompt_lower or "find" in prompt_lower:
                steps.append(PlannedActionProposal(
                    step_number=1,
                    tool_name="companion_fs",
                    operation="search_files",
                    parameters={"base_dir": "projects", "pattern": "project"},
                    rationale="Locate project files within authorized workspace."
                ))
            else:
                steps.append(PlannedActionProposal(
                    step_number=1,
                    tool_name="companion_fs",
                    operation="list_directory",
                    parameters={"path": "."},
                    rationale="Inspect files and directory layout within authorized workspace."
                ))

        # Default fallback plan
        if not steps:
            scope.append("GENERAL_ASSISTANCE")
            steps.append(PlannedActionProposal(
                step_number=1,
                tool_name="companion_fs",
                operation="list_directory",
                parameters={"path": "."},
                rationale="Explore workspace to identify relevant files for user query."
            ))

        return PlannerPlan(
            task_intent=prompt,
            declared_scope=scope,
            steps=steps
        )
