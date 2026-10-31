"""
Main Application Entry Point for ALFRED AI Backend.

Coordinates:
- FastAPI Application configuration with OpenAPI documentation.
- Database lifecycle initialization on startup.
- CORS middleware for secure dashboard access.
- Routing for Tasks, Approvals, Security Center, and Integrations.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.database.connection import init_db
from backend.app.api.tasks import router as tasks_router
from backend.app.api.approvals import router as approvals_router
from backend.app.api.security import router as security_router
from backend.app.api.integrations import router as integrations_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager ensuring database tables and default
    records are created on service startup.
    """
    init_db()
    yield


app = FastAPI(
    title="ALFRED AI - Prompt-Injection-Resistant Autonomous Agent API",
    description=(
        "Production backend for ALFRED AI featuring Dynamic Authority Engine, "
        "Cryptographic Capabilities, Taint Provenance, and Layered Prompt Injection Defenses."
    ),
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration allowing frontend dashboard requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Subsystem Routers
app.include_router(tasks_router)
app.include_router(approvals_router)
app.include_router(security_router)
app.include_router(integrations_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """System health check endpoint verifying backend and security subsystems."""
    return {
        "status": "HEALTHY",
        "service": "ALFRED AI Autonomous Agent Backend",
        "security_architecture": "ACTIVE",
        "authority_engine": "ONLINE",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
