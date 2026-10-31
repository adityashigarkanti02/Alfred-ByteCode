"""
Authentication and Request Integrity for ALFRED AI Local Companion.

Because the local companion operates with local filesystem privileges, it must
never rely on network proximity or CORS alone. All inbound requests must present:
1. A valid Companion Secret Token (via X-Companion-Token header)
2. Or a signed HMAC request header verifying caller identity.
"""

import hmac
import hashlib
import os
from typing import Optional
from fastapi import Header, HTTPException, status

# Default companion secret; production deployments supply a randomized secret
COMPANION_API_SECRET = os.getenv(
    "ALFRED_COMPANION_SECRET",
    "alfred-companion-secure-token-local-99218204"
)


def verify_companion_token(x_companion_token: Optional[str] = Header(None)) -> str:
    """
    FastAPI dependency enforcing strict token authentication on all filesystem endpoints.
    Fails closed with 401 Unauthorized if token is missing or incorrect.
    """
    if not x_companion_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required X-Companion-Token header for local filesystem operation"
        )

    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(x_companion_token, COMPANION_API_SECRET):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid companion token. Local filesystem access denied."
        )

    return x_companion_token
