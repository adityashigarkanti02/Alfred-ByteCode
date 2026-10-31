"""
Main entry point for ALFRED AI Local Companion Service.

Runs on http://127.0.0.1:8001 to provide secure, local filesystem interaction
exclusively to the authenticated ALFRED AI backend.
"""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
try:
    from security.path_validator import PathValidator
    from filesystem.operations import CompanionFilesystemManager
    from api.routes import router as fs_router, set_filesystem_manager
except (ImportError, ValueError):
    from ..security.path_validator import PathValidator
    from ..filesystem.operations import CompanionFilesystemManager
    from ..api.routes import router as fs_router, set_filesystem_manager

app = FastAPI(
    title="ALFRED AI - Local Companion Service",
    description="Secure, isolated local filesystem agent for ALFRED AI",
    version="1.0.0"
)

# CORS configuration strictly restricted to localhost origin
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

# Initialize authorized directories
# Default authorized sandbox directory in user workspace
DEFAULT_SANDBOX_DIR = os.getenv(
    "ALFRED_SANDBOX_DIR",
    str(Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "workspace_sandbox")
)

path_validator = PathValidator(authorized_roots=[DEFAULT_SANDBOX_DIR])
fs_manager = CompanionFilesystemManager(validator=path_validator)
set_filesystem_manager(fs_manager)

app.include_router(fs_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify companion availability and authorized roots."""
    return {
        "status": "HEALTHY",
        "service": "ALFRED AI Local Companion",
        "authorized_roots_count": len(path_validator.authorized_roots),
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    # Bind strictly to localhost (never 0.0.0.0 for the local companion)
    port = int(os.getenv("COMPANION_PORT", "8001"))
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=False)
