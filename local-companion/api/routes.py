"""
REST API Endpoints for ALFRED AI Local Companion Service.

Exposes restricted filesystem operations to the ALFRED backend.
All endpoints require authentication via X-Companion-Token and strictly validate
paths against authorized directory boundaries.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
try:
    from security.auth import verify_companion_token
    from security.path_validator import PathValidator, PathSecurityException
    from filesystem.operations import CompanionFilesystemManager
except (ImportError, ValueError):
    from ..security.auth import verify_companion_token
    from ..security.path_validator import PathValidator, PathSecurityException
    from ..filesystem.operations import CompanionFilesystemManager

router = APIRouter(prefix="/api/v1/fs", tags=["Local Filesystem"])

# Shared global filesystem manager initialized by main app
_manager: Optional[CompanionFilesystemManager] = None


def set_filesystem_manager(manager: CompanionFilesystemManager) -> None:
    """Injects the initialized manager instance."""
    global _manager
    _manager = manager


def get_manager() -> CompanionFilesystemManager:
    """Dependency retrieving the active CompanionFilesystemManager."""
    if _manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Filesystem manager not initialized"
        )
    return _manager


# Request & Response Schemas
class ListDirRequest(BaseModel):
    path: str = Field(description="Target directory path to inspect")


class ReadFileRequest(BaseModel):
    path: str = Field(description="Target file path to read")
    max_bytes: int = Field(default=5_000_000, description="Maximum bytes to read")


class WriteFileRequest(BaseModel):
    path: str = Field(description="Target file path to write")
    content: str = Field(description="Text payload to write")
    overwrite: bool = Field(default=True, description="Whether to overwrite existing file")


class EditFileRequest(BaseModel):
    path: str = Field(description="Target file path to modify")
    find_text: str = Field(description="Exact substring to find")
    replace_text: str = Field(description="Replacement string")


class SearchFilesRequest(BaseModel):
    base_dir: str = Field(description="Base directory to search recursively")
    pattern: str = Field(description="Substring to match in filenames")


class MoveFileRequest(BaseModel):
    source_path: str = Field(description="Existing file path")
    dest_path: str = Field(description="Target destination path")


class DeleteFileRequest(BaseModel):
    path: str = Field(description="Target file path to delete")
    confirmed: bool = Field(default=False, description="Explicit operator confirmation flag")


class AuthorizeRootRequest(BaseModel):
    directory_path: str = Field(description="New directory to authorize as accessible workspace root")


# API Routes
@router.get("/authorized-roots", dependencies=[Depends(verify_companion_token)])
async def get_authorized_roots(manager: CompanionFilesystemManager = Depends(get_manager)) -> Dict[str, Any]:
    """Returns the list of currently authorized directory roots."""
    return {"authorized_roots": manager.validator.authorized_roots}


@router.post("/authorize-root", dependencies=[Depends(verify_companion_token)])
async def authorize_root(
    req: AuthorizeRootRequest,
    manager: CompanionFilesystemManager = Depends(get_manager)
) -> Dict[str, Any]:
    """Adds a new local directory to the authorized roots whitelist."""
    try:
        canonical = manager.validator.add_authorized_root(req.directory_path)
        return {"status": "AUTHORIZED", "canonical_path": canonical}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/list", dependencies=[Depends(verify_companion_token)])
async def list_directory(
    req: ListDirRequest,
    manager: CompanionFilesystemManager = Depends(get_manager)
) -> Dict[str, Any]:
    """Lists files and folders within an authorized directory."""
    try:
        entries = manager.list_directory(req.path)
        return {"path": req.path, "entries": entries}
    except PathSecurityException as pse:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pse))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/read", dependencies=[Depends(verify_companion_token)])
async def read_file(
    req: ReadFileRequest,
    manager: CompanionFilesystemManager = Depends(get_manager)
) -> Dict[str, Any]:
    """Reads a text, PDF, or DOCX document from an authorized directory."""
    try:
        return manager.read_file(req.path, max_bytes=req.max_bytes)
    except PathSecurityException as pse:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pse))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/write", dependencies=[Depends(verify_companion_token)])
async def write_file(
    req: WriteFileRequest,
    manager: CompanionFilesystemManager = Depends(get_manager)
) -> Dict[str, Any]:
    """Safely creates or overwrites a file within an authorized directory."""
    try:
        return manager.write_file(req.path, req.content, overwrite=req.overwrite)
    except PathSecurityException as pse:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pse))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/edit", dependencies=[Depends(verify_companion_token)])
async def edit_file(
    req: EditFileRequest,
    manager: CompanionFilesystemManager = Depends(get_manager)
) -> Dict[str, Any]:
    """Applies find-and-replace edits to a file within an authorized directory."""
    try:
        return manager.edit_file(req.path, req.find_text, req.replace_text)
    except PathSecurityException as pse:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pse))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/search", dependencies=[Depends(verify_companion_token)])
async def search_files(
    req: SearchFilesRequest,
    manager: CompanionFilesystemManager = Depends(get_manager)
) -> Dict[str, Any]:
    """Recursively searches for matching filenames within an authorized directory."""
    try:
        matches = manager.search_files(req.base_dir, req.pattern)
        return {"base_dir": req.base_dir, "matches": matches}
    except PathSecurityException as pse:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pse))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/move", dependencies=[Depends(verify_companion_token)])
async def move_file(
    req: MoveFileRequest,
    manager: CompanionFilesystemManager = Depends(get_manager)
) -> Dict[str, Any]:
    """Moves or renames a file between authorized locations."""
    try:
        return manager.move_file(req.source_path, req.dest_path)
    except PathSecurityException as pse:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pse))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/delete", dependencies=[Depends(verify_companion_token)])
async def delete_file(
    req: DeleteFileRequest,
    manager: CompanionFilesystemManager = Depends(get_manager)
) -> Dict[str, Any]:
    """Deletes a file after operator confirmation within an authorized directory."""
    try:
        return manager.delete_file(req.path, confirmed=req.confirmed)
    except PathSecurityException as pse:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pse))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
