"""
LangGraph Controlled Execution Workflow for ALFRED AI.

Implements a deterministic state-machine workflow that enforces:
1. Decoupled planning from execution.
2. Mandatory Security Evaluation gate before every tool invocation.
3. Checkpointed pauses for L2 Human Approvals.
4. Taint and prompt injection monitoring during ingestion.
5. Tamper-evident state recording and final report generation.
"""

from typing import Dict, List, Any, Optional, TypedDict, Annotated
from pydantic import BaseModel
from langgraph.graph import StateGraph, END

from backend.app.agent.planner.planner import AgentPlanner, PlannedActionProposal, PlannerPlan
from backend.app.agent.executor.gateway import SecureToolGateway, ToolExecutionResult
from backend.app.security.authority_engine.engine import DynamicAuthorityEngine, AuthorityEvaluationResult
from backend.app.security.policy_engine.engine import PolicyDecision, AuthorityLevel
from backend.app.security.capability_manager.manager import CapabilityPayload
from backend.app.security.provenance.tracker import ProvenanceTracker, TrustLabel
from backend.app.security.injection_detector.detector import PromptInjectionDetector, DetectionResult


class WorkflowState(TypedDict):
    """
    State tracked across all nodes in the LangGraph workflow.
    """
    task_id: str
    user_id: str
    prompt: str
    status: str  # PLANNING, EXECUTING, AWAITING_APPROVAL, COMPLETED, FAILED, BLOCKED_ATTACK
    plan: Optional[Dict[str, Any]]
    current_step_index: int
    executed_steps: List[Dict[str, Any]]
    active_capability: Optional[Dict[str, Any]]
    pending_approval: Optional[Dict[str, Any]]
    security_events: List[Dict[str, Any]]
    final_report: Optional[str]
    circuit_breaker_tripped: bool


class AlfredWorkflowEngine:
    """
    Builds and executes the controlled LangGraph workflow.
    """

    def __init__(
        self,
        planner: Optional[AgentPlanner] = None,
        authority_engine: Optional[DynamicAuthorityEngine] = None,
        tool_gateway: Optional[SecureToolGateway] = None,
        injection_detector: Optional[PromptInjectionDetector] = None
    ):
        self.planner = planner or AgentPlanner()
        self.authority_engine = authority_engine or DynamicAuthorityEngine()
        self.tool_gateway = tool_gateway or SecureToolGateway()
        self.injection_detector = injection_detector or PromptInjectionDetector()
        
        # Build LangGraph workflow
        self.graph = self._build_graph()

    def _build_graph(self):
        """Assembles the LangGraph state machine."""
        workflow = StateGraph(WorkflowState)

        # Add Nodes
        workflow.add_node("plan_task", self._plan_node)
        workflow.add_node("evaluate_security", self._evaluate_security_node)
        workflow.add_node("execute_tool", self._execute_tool_node)
        workflow.add_node("finalize_report", self._finalize_report_node)

        # Set Entry Point
        workflow.set_entry_point("plan_task")

        # Routing from plan_task
        workflow.add_edge("plan_task", "evaluate_security")

        # Conditional routing from evaluate_security
        def route_after_security(state: WorkflowState):
            if state.get("circuit_breaker_tripped"):
                return "finalize_report"
            if state.get("status") == "AWAITING_APPROVAL":
                return END  # Pauses workflow awaiting human approval
            if state.get("status") == "BLOCKED_ATTACK":
                return "finalize_report"
            if state.get("active_capability"):
                return "execute_tool"
            return "finalize_report"

        workflow.add_conditional_edges(
            "evaluate_security",
            route_after_security,
            {
                "execute_tool": "execute_tool",
                "finalize_report": "finalize_report",
                END: END
            }
        )

        # Conditional routing from execute_tool
        def route_after_execution(state: WorkflowState):
            if state.get("circuit_breaker_tripped"):
                return "finalize_report"
            # If more steps remain in plan
            plan = state.get("plan", {})
            steps = plan.get("steps", []) if plan else []
            if state.get("current_step_index", 0) < len(steps):
                return "evaluate_security"
            return "finalize_report"

        workflow.add_conditional_edges(
            "execute_tool",
            route_after_execution,
            {
                "evaluate_security": "evaluate_security",
                "finalize_report": "finalize_report"
            }
        )

        workflow.add_edge("finalize_report", END)

        return workflow.compile()

    def _plan_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Formulates task plan without executing actions."""
        plan_obj = self.planner.plan_task(state["prompt"])
        return {
            "status": "EXECUTING",
            "plan": plan_obj.model_dump(),
            "current_step_index": 0,
            "executed_steps": [],
            "security_events": []
        }

    def _evaluate_security_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Evaluates the proposed action at the independent authority boundary."""
        plan = state.get("plan")
        if not plan:
            return {"status": "FAILED", "final_report": "Execution plan was empty"}

        steps = plan.get("steps", [])
        idx = state.get("current_step_index", 0)
        if idx >= len(steps):
            return {"status": "COMPLETED"}

        step = steps[idx]
        eval_result = self.authority_engine.evaluate_proposal(
            user_id=state["user_id"],
            task_id=state["task_id"],
            tool_name=step["tool_name"],
            operation=step["operation"],
            parameters=step["parameters"],
            task_intent=state["prompt"]
        )

        if eval_result.circuit_breaker_tripped:
            return {
                "status": "BLOCKED_ATTACK",
                "circuit_breaker_tripped": True,
                "final_report": f"Task halted: Emergency Circuit Breaker tripped ({eval_result.rationale})"
            }

        if eval_result.decision == PolicyDecision.DENY:
            # Action blocked by policy
            event = {
                "threat_category": "POLICY_DENIAL",
                "risk_score": 0.9,
                "explanation": eval_result.rationale,
                "step_number": step["step_number"],
                "tool": f"{step['tool_name']}:{step['operation']}"
            }
            events = state.get("security_events", []) + [event]
            return {
                "status": "BLOCKED_ATTACK",
                "security_events": events,
                "final_report": f"Operation denied by security policy: {eval_result.rationale}"
            }

        if eval_result.decision == PolicyDecision.REQUIRE_APPROVAL:
            approval_record = {
                "approval_id": f"appr_{state['task_id'][:8]}_{idx}",
                "task_id": state["task_id"],
                "step_number": step["step_number"],
                "tool_name": step["tool_name"],
                "operation": step["operation"],
                "parameters": step["parameters"],
                "explanation": eval_result.rationale,
                "status": "PENDING"
            }
            return {
                "status": "AWAITING_APPROVAL",
                "pending_approval": approval_record
            }

        # Operation is ALLOWED -> Store issued Capability
        cap_dict = eval_result.capability.model_dump() if eval_result.capability else None
        # Convert datetime to ISO string for JSON serialization
        if cap_dict and "expiration" in cap_dict and not isinstance(cap_dict["expiration"], str):
            cap_dict["expiration"] = cap_dict["expiration"].isoformat()

        return {
            "active_capability": cap_dict,
            "status": "EXECUTING"
        }

    def _execute_tool_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Executes tool via Secure Tool Gateway and stamps provenance."""
        plan = state.get("plan", {})
        steps = plan.get("steps", [])
        idx = state["current_step_index"]
        step = steps[idx]
        cap_dict = state["active_capability"]

        # Reconstruct CapabilityPayload
        cap_payload = CapabilityPayload(**cap_dict)

        result: ToolExecutionResult = self.tool_gateway.execute_tool(
            task_id=state["task_id"],
            user_prompt=state["prompt"],
            tool_name=step["tool_name"],
            operation=step["operation"],
            parameters=step["parameters"],
            capability=cap_payload
        )

        executed_record = {
            "step_number": step["step_number"],
            "tool_name": step["tool_name"],
            "operation": step["operation"],
            "parameters": step["parameters"],
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "is_tainted": result.is_tainted,
            "provenance_hash": result.provenance_hash
        }

        executed_steps = state.get("executed_steps", []) + [executed_record]
        security_events = state.get("security_events", [])

        # Log security event if detected during external payload ingestion
        if result.security_event_detected and result.detection_result:
            det = result.detection_result
            security_events.append({
                "threat_category": det.threat_category,
                "risk_score": det.risk_score,
                "explanation": det.explanation,
                "suspicious_excerpt": det.suspicious_excerpt,
                "source": det.source
            })

        return {
            "current_step_index": idx + 1,
            "executed_steps": executed_steps,
            "security_events": security_events,
            "active_capability": None
        }

    def _finalize_report_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Prepares comprehensive, human-readable execution summary."""
        total_steps = len(state.get("executed_steps", []))
        sec_count = len(state.get("security_events", []))
        
        status = state.get("status", "COMPLETED")
        if status not in ("BLOCKED_ATTACK", "FAILED"):
            status = "COMPLETED"

        report = (
            f"### ALFRED AI Task Execution Report\n\n"
            f"- **Status**: {status}\n"
            f"- **Completed Steps**: {total_steps}\n"
            f"- **Security Incidents Intercepted**: {sec_count}\n"
        )
        if sec_count > 0:
            report += "\n#### Security Defenses Triggered:\n"
            for ev in state["security_events"]:
                report += f"- **[{ev.get('threat_category', 'THREAT')}]** {ev.get('explanation', '')}\n"

        return {
            "status": status,
            "final_report": report
        }

    def run_task(self, task_id: str, user_id: str, prompt: str) -> WorkflowState:
        """Runs the workflow synchronously until pause or completion."""
        initial_state: WorkflowState = {
            "task_id": task_id,
            "user_id": user_id,
            "prompt": prompt,
            "status": "PLANNING",
            "plan": None,
            "current_step_index": 0,
            "executed_steps": [],
            "active_capability": None,
            "pending_approval": None,
            "security_events": [],
            "final_report": None,
            "circuit_breaker_tripped": False
        }
        return self.graph.invoke(initial_state)

    def resume_with_approval(self, state: WorkflowState, approved: bool) -> WorkflowState:
        """
        Resumes a paused workflow after human approval decision.
        """
        if not approved:
            state["status"] = "CANCELLED"
            state["final_report"] = "Operation cancelled by user rejection."
            return state

        # Human approved -> issue capability for the pending step
        plan = state["plan"]
        idx = state["current_step_index"]
        step = plan["steps"][idx]

        # Extract parameters
        cap = self.authority_engine.capability_manager.issue_capability(
            user_id=state["user_id"],
            task_id=state["task_id"],
            authorized_tool=step["tool_name"],
            exact_operation=step["operation"],
            resource_scope=str(step["parameters"].get("path") or "*"),
            permitted_destination=str(step["parameters"].get("destination") or step["parameters"].get("recipient") or "") or None
        )
        cap_dict = cap.model_dump()
        cap_dict["expiration"] = cap_dict["expiration"].isoformat()

        state["active_capability"] = cap_dict
        state["status"] = "EXECUTING"
        state["pending_approval"] = None

        # Resume execution node
        exec_update = self._execute_tool_node(state)
        state.update(exec_update)

        # Check if more steps remain
        steps = plan.get("steps", [])
        if state["current_step_index"] < len(steps):
            return self.graph.invoke(state)
        else:
            final_update = self._finalize_report_node(state)
            state.update(final_update)
            return state
