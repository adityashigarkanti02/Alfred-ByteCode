"""
Security Center and Authority Analytics API Endpoints for ALFRED AI.

Exposes real-time threat detection telemetry, deterministic policy rulings,
cryptographic capability lists, and emergency circuit breaker controls.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.services.security_service import SecurityService
from backend.app.security.injection_detector.detector import PromptInjectionDetector, DetectionResult

router = APIRouter(prefix="/api/v1/security", tags=["Security Center"])


class InspectTextRequest(BaseModel):
    """Payload to directly test and inspect text for prompt injections."""
    text: str = Field(description="Content to inspect")
    source: Optional[str] = Field(default="MANUAL_INSPECTION", description="Source identifier")


class CircuitBreakerResetRequest(BaseModel):
    """Payload to reset emergency circuit breaker on a task."""
    task_id: str = Field(description="Task identifier to reset")


@router.get("/dashboard")
async def get_dashboard_metrics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieves live metrics for the main system dashboard."""
    service = SecurityService(db=db)
    return service.get_dashboard_metrics()


@router.get("/events")
async def get_security_events(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieves security incidents, policy decisions, and audit logs for the Security Center."""
    service = SecurityService(db=db)
    return service.get_security_center_data()


@router.get("/authority")
async def get_authority_center_data(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieves active capabilities and approval histories for the Authority Center."""
    service = SecurityService(db=db)
    return service.get_authority_center_data()


@router.post("/inspect")
async def inspect_content(req: InspectTextRequest) -> DetectionResult:
    """
    Directly runs the Prompt Injection Defense Engine on any text payload.
    Used for ad-hoc inspection and security testing.
    """
    detector = PromptInjectionDetector()
    return detector.inspect_text(req.text, source=req.source or "MANUAL_INSPECTION")


@router.post("/circuit-breaker/reset")
async def reset_circuit_breaker(
    req: CircuitBreakerResetRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Resets the emergency circuit breaker for a task."""
    from backend.app.models.entities import Task
    task = db.query(Task).filter(Task.id == req.task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{req.task_id}' not found")

    task.circuit_breaker_triggered = False
    db.commit()
    return {"status": "RESET", "task_id": req.task_id}
