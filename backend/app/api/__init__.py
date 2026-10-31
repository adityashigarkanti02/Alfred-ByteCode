"""
Export API routers for ALFRED AI backend.
"""

from backend.app.api.tasks import router as tasks_router
from backend.app.api.approvals import router as approvals_router
from backend.app.api.security import router as security_router
from backend.app.api.integrations import router as integrations_router

__all__ = [
    "tasks_router",
    "approvals_router",
    "security_router",
    "integrations_router",
]
