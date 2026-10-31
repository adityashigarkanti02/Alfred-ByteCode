"""
Approval API Endpoints for ALFRED AI.

Enables viewing and resolving L2 Human Approval requests for sensitive actions
(e.g., outbound email sending, file deletion, setting modifications).
Approvals are immutably bound to exact action parameters.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.entities import Approval, Task
from backend.app.services.task_service import TaskService

router = APIRouter(prefix="/api/v1/approvals", tags=["Approvals"])


class ApprovalDecisionRequest(BaseModel):
    """Payload to authorize or reject a pending operation."""
    approved: bool = Field(description="True to authorize execution, False to reject")
    decided_by: Optional[str] = Field(default="OPERATOR", description="Identity of approving human operator")


@router.get("")
async def list_approvals(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Lists approvals, optionally filtered by status (PENDING, APPROVED, REJECTED)."""
    query = db.query(Approval)
    if status_filter:
        query = query.filter(Approval.status == status_filter.upper())
    
    approvals = query.order_by(Approval.created_at.desc()).limit(50).all()
    return [
        {
            "id": a.id,
            "task_id": a.task_id,
            "tool_name": a.tool_name,
            "operation": a.operation,
            "parameters": a.parameters,
            "explanation": a.explanation,
            "status": a.status,
            "decided_by": a.decided_by,
            "decided_at": a.decided_at.isoformat() if a.decided_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in approvals
    ]


@router.post("/{task_id}/decide")
async def decide_approval(
    task_id: str,
    req: ApprovalDecisionRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Submits a human approval decision for a paused task and resumes agent execution.
    """
    service = TaskService(db=db)
    try:
        result = service.resolve_approval(
            task_id=task_id,
            approved=req.approved,
            decided_by=req.decided_by or "OPERATOR"
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
