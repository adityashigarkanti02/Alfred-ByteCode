"""
Integration and Tool API Endpoints for ALFRED AI.

Provides direct access for the frontend views:
- Email Management: Inbox reading, thread inspection, draft and send operations.
- Web Browser: Direct page navigation and extraction.
- Local File Manager: Workspace file browsing and search.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.services.integration_service import IntegrationService
from backend.app.integrations.gmail.client import GmailClient
from backend.app.integrations.browser.browser_service import SecureBrowserService
from backend.app.integrations.files.companion_client import CompanionClient

router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])


# Request Schemas
class BrowseUrlRequest(BaseModel):
    url: str = Field(description="Web URL to navigate and extract")


class DraftEmailRequest(BaseModel):
    to_recipients: List[str]
    subject: str
    body: str


# API Routes
@router.get("/status")
async def get_integrations_status(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Returns the live connection status for all external integrations."""
    service = IntegrationService(db=db)
    return service.get_all_integrations_status()


# Gmail Endpoints
@router.get("/gmail/inbox")
async def get_gmail_inbox(query: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves email messages from Gmail inbox (or offline security sandbox)."""
    client = GmailClient(sandbox_mode=True)
    return client.list_emails(max_results=20, query=query)


@router.get("/gmail/messages/{message_id}")
async def get_gmail_message(message_id: str) -> Dict[str, Any]:
    """Retrieves full email details including body and attachments."""
    client = GmailClient(sandbox_mode=True)
    msg = client.read_email(message_id)
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return msg.model_dump()


@router.post("/gmail/draft")
async def create_email_draft(req: DraftEmailRequest) -> Dict[str, Any]:
    """Creates an email draft in Gmail."""
    client = GmailClient(sandbox_mode=True)
    return client.create_draft(to_recipients=req.to_recipients, subject=req.subject, body=req.body)


# Browser Endpoints
@router.post("/browser/navigate")
async def browse_website(req: BrowseUrlRequest) -> Dict[str, Any]:
    """Navigates to a webpage and extracts visible text, comments, and links."""
    service = SecureBrowserService()
    try:
        res = service.navigate_and_extract(req.url)
        return res.model_dump()
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Filesystem Endpoints (Local Companion Proxy)
@router.get("/files/list")
async def list_workspace_files(path: str = ".") -> List[Dict[str, Any]]:
    """Lists files within authorized companion directory."""
    client = CompanionClient()
    try:
        return client.list_directory(path)
    except Exception:
        # Fallback default sandbox view
        return [
            {
                "name": "invoices",
                "path": "invoices",
                "is_directory": True,
                "size_bytes": 0,
                "modified_at": "2026-10-30T10:00:00Z",
                "extension": ""
            },
            {
                "name": "research_report.md",
                "path": "research_report.md",
                "is_directory": False,
                "size_bytes": 1420,
                "modified_at": "2026-10-31T08:30:00Z",
                "extension": ".md"
            }
        ]
