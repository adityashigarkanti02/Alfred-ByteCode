"""
Task API Endpoints for ALFRED AI.

Enables submitting natural-language autonomous tasks, querying task progress,
inspecting tool calls, and reviewing final execution reports.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.entities import Task, TaskStep, ToolCall, generate_uuid
from backend.app.services.task_service import TaskService

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


class CreateTaskRequest(BaseModel):
    """Payload to launch an autonomous agent task."""
    prompt: str = Field(description="Natural-language instruction for the agent")
    user_id: Optional[str] = Field(default="user_default_operator", description="Principal user ID")


class TaskSummaryResponse(BaseModel):
    """High-level task summary."""
    id: str
    prompt: str
    status: str
    created_at: str
    final_report: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_task(req: CreateTaskRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Submits a natural-language task. The agent plans, security checks, and executes the task.
    """
    if not req.prompt.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task prompt cannot be empty")

    service = TaskService(db=db)
    result = service.create_and_run_task(user_id=req.user_id, prompt=req.prompt)
    return result


@router.get("")
async def list_tasks(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Lists all tasks sorted by creation date."""
    tasks = db.query(Task).order_by(Task.created_at.desc()).offset(offset).limit(limit).all()
    return [
        {
            "id": t.id,
            "prompt": t.natural_language_prompt,
            "status": t.status,
            "circuit_breaker_triggered": t.circuit_breaker_triggered,
            "final_report": t.final_report,
            "created_at": t.created_at.isoformat() if t.created_at else None
        }
        for t in tasks
    ]


@router.get("/{task_id}")
async def get_task_details(task_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieves full task execution details including tool calls and security decisions."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found")

    tool_calls = db.query(ToolCall).filter(ToolCall.task_id == task_id).all()

    return {
        "id": task.id,
        "prompt": task.natural_language_prompt,
        "status": task.status,
        "circuit_breaker_triggered": task.circuit_breaker_triggered,
        "final_report": task.final_report,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "tool_calls": [
            {
                "id": tc.id,
                "tool_name": tc.tool_name,
                "operation": tc.operation,
                "arguments": tc.arguments,
                "status": tc.status,
                "execution_result": tc.execution_result,
                "error_message": tc.error_message,
                "created_at": tc.created_at.isoformat() if tc.created_at else None
            }
            for tc in tool_calls
        ]
    }


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Cancels an active or paused task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found")

    task.status = "CANCELLED"
    db.commit()
    return {"task_id": task_id, "status": "CANCELLED"}
