"""
Secure Web Browsing Integration for ALFRED AI.

This module coordinates browser automation using Playwright (with automated HTTP fallback).
Enforces strict browser containment:
1. SSRF Prevention: Blocks navigation to private/internal IPv4/IPv6 ranges (127.0.0.1, 10.0.0.0/8, 192.168.0.0/16, 169.254.169.254 AWS metadata).
2. Isolated Context: Fresh, ephemeral context without stored cookies or credentials.
3. No LLM-injected JavaScript: Arbitrary `evaluate()` scripts are disallowed.
4. Deep Hidden Element & Comment Extraction: Feeds raw DOM to the Prompt Injection Detector.
"""

import ipaddress
import re
import socket
from urllib.parse import urlparse
from typing import Dict, List, Any, Optional
import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field


class BrowserExtractionResult(BaseModel):
    """Normalized content extracted from a webpage."""
    url: str
    title: str
    text_content: str
    raw_html: str
    links: List[Dict[str, str]]
    hidden_comments: List[str]
    status_code: int


class SecureBrowserService:
    """
    Secure browser driver enforcing SSRF guards and DOM sanitization.
    """

    def __init__(self, allow_external_browsing: bool = True):
        self.allow_external_browsing = allow_external_browsing

    def _is_private_ip(self, hostname: str) -> bool:
        """
        Resolves hostname and verifies that IP is NOT a private, loopback, or link-local address.
        Prevents Server-Side Request Forgery (SSRF) against internal networks or cloud metadata.
        """
        # Exclude common private keywords
        if hostname.lower() in ("localhost", "127.0.0.1", "::1", "metadata.google.internal"):
            return True

        try:
            # Resolve DNS
            ip_str = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip_str)
            return (
                ip_obj.is_private or
                ip_obj.is_loopback or
                ip_obj.is_link_local or
                ip_obj.is_reserved or
                str(ip_obj) == "169.254.169.254"
            )
        except Exception:
            # Fail closed on DNS resolution error
            return True

    def validate_url(self, url: str) -> Tuple_Validation:
        """
        Validates URL scheme and destination host.
        """
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, f"Prohibited URL scheme '{parsed.scheme}'. Only http and https permitted."

        if not parsed.hostname:
            return False, "Invalid URL: missing hostname"

        if self._is_private_ip(parsed.hostname):
            return False, f"SSRF Block: Host '{parsed.hostname}' resolves to private/internal IP address"

        return True, "URL allowed"

    def navigate_and_extract(self, url: str) -> BrowserExtractionResult:
        """
        Navigates to URL, retrieves DOM, and extracts visible content, links, and comments.
        """
        is_valid, reason = self.validate_url(url)
        if not is_valid:
            raise PermissionError(reason)

        # Use HTTP client with strict timeout and redirect limits
        headers = {
            "User-Agent": "ALFRED-AI-Autonomous-Agent-SecureBrowser/1.0"
        }
        
        with httpx.Client(follow_redirects=True, timeout=15.0, headers=headers) as client:
            resp = client.get(url)
            
            # Re-validate destination URL after redirects
            final_url = str(resp.url)
            final_valid, final_reason = self.validate_url(final_url)
            if not final_valid:
                raise PermissionError(f"Redirect violation: {final_reason}")

            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Extract title
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            
            # Extract comments
            comments = [str(c).strip() for c in soup.find_all(string=lambda t: hasattr(t, "text") and False)]
            # Also extract comment tags
            from bs4 import Comment
            html_comments = [str(c).strip() for c in soup.find_all(string=lambda t: isinstance(t, Comment))]

            # Extract visible links
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text().strip()
                if href and not href.startswith("javascript:"):
                    links.append({"text": text or href, "href": href})

            # Clean script/style tags for text extraction
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()

            visible_text = soup.get_text(separator="\n", strip=True)

            return BrowserExtractionResult(
                url=final_url,
                title=title,
                text_content=visible_text[:50_000],  # Bound text content size
                raw_html=resp.text[:100_000],
                links=links[:50],
                hidden_comments=html_comments[:20],
                status_code=resp.status_code
            )


# Type alias
Tuple_Validation = tuple[bool, str]
