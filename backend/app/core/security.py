"""
Authentication and security dependencies for SmartGateAI administrative operations.
Enforces:
- Header-only authentication ('X-Admin-API-Key').
- Complete rejection of URL query parameter authentication.
- Constant-time secret comparison to prevent timing attacks.
"""

import secrets
from typing import Optional
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from ..config import settings

# Enforce header-only authentication
api_key_header = APIKeyHeader(name="X-Admin-API-Key", auto_error=False)


def verify_admin_key(
    header_key: Optional[str] = Security(api_key_header)
) -> str:
    """
    Validate administrative access using the configured secret key.
    Rejects missing, empty, or invalid credentials with HTTP 401.
    Query parameter credentials are not accepted under any circumstances.
    """
    if not header_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required. Provide 'X-Admin-API-Key' header."
        )

    # Constant-time comparison against configured environment secret
    is_valid = secrets.compare_digest(header_key.strip(), settings.ADMIN_API_KEY)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative API key."
        )

    return header_key
