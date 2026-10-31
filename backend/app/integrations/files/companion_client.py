"""
Backend Client for ALFRED AI Local Companion Filesystem Service.

Dispatches filesystem and document operations to the isolated Local Companion
running on http://127.0.0.1:8001 using authenticated HTTP requests.
Includes fallback support for local execution during integrated tests.
"""

import os
from typing import Dict, List, Any, Optional
import httpx


class CompanionClient:
    """
    Communicates with the Local Companion service via authenticated HTTP.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        secret_token: Optional[str] = None
    ):
        self.base_url = (base_url or os.getenv("COMPANION_URL", "http://127.0.0.1:8001")).rstrip("/")
        self.secret_token = secret_token or os.getenv(
            "ALFRED_COMPANION_SECRET",
            "alfred-companion-secure-token-local-99218204"
        )

    def _headers(self) -> Dict[str, str]:
        """Injects authentication headers."""
        return {
            "X-Companion-Token": self.secret_token,
            "Content-Type": "application/json"
        }

    def get_authorized_roots(self) -> List[str]:
        """Queries the companion for configured authorized directories."""
        url = f"{self.base_url}/api/v1/fs/authorized-roots"
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(url, headers=self._headers())
            resp.raise_for_status()
            return resp.json().get("authorized_roots", [])

    def authorize_root(self, directory_path: str) -> Dict[str, Any]:
        """Adds a new authorized directory to the companion whitelist."""
        url = f"{self.base_url}/api/v1/fs/authorize-root"
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(url, headers=self._headers(), json={"directory_path": directory_path})
            resp.raise_for_status()
            return resp.json()

    def list_directory(self, path: str) -> List[Dict[str, Any]]:
        """Lists directory entries."""
        url = f"{self.base_url}/api/v1/fs/list"
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=self._headers(), json={"path": path})
            resp.raise_for_status()
            return resp.json().get("entries", [])

    def read_file(self, path: str) -> Dict[str, Any]:
        """Reads file content or extracts document text."""
        url = f"{self.base_url}/api/v1/fs/read"
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, headers=self._headers(), json={"path": path})
            resp.raise_for_status()
            return resp.json()

    def write_file(self, path: str, content: str, overwrite: bool = True) -> Dict[str, Any]:
        """Creates or writes file content."""
        url = f"{self.base_url}/api/v1/fs/write"
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                url,
                headers=self._headers(),
                json={"path": path, "content": content, "overwrite": overwrite}
            )
            resp.raise_for_status()
            return resp.json()

    def edit_file(self, path: str, find_text: str, replace_text: str) -> Dict[str, Any]:
        """Edits targeted text within file."""
        url = f"{self.base_url}/api/v1/fs/edit"
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                url,
                headers=self._headers(),
                json={"path": path, "find_text": find_text, "replace_text": replace_text}
            )
            resp.raise_for_status()
            return resp.json()

    def search_files(self, base_dir: str, pattern: str) -> List[Dict[str, Any]]:
        """Searches files by name pattern."""
        url = f"{self.base_url}/api/v1/fs/search"
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                url,
                headers=self._headers(),
                json={"base_dir": base_dir, "pattern": pattern}
            )
            resp.raise_for_status()
            return resp.json().get("matches", [])

    def move_file(self, source_path: str, dest_path: str) -> Dict[str, Any]:
        """Moves or renames a file."""
        url = f"{self.base_url}/api/v1/fs/move"
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                url,
                headers=self._headers(),
                json={"source_path": source_path, "dest_path": dest_path}
            )
            resp.raise_for_status()
            return resp.json()

    def delete_file(self, path: str, confirmed: bool = False) -> Dict[str, Any]:
        """Deletes a file."""
        url = f"{self.base_url}/api/v1/fs/delete"
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                url,
                headers=self._headers(),
                json={"path": path, "confirmed": confirmed}
            )
            resp.raise_for_status()
            return resp.json()
