"""Dependency functions for route handlers."""

import logging

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token
from app.core.settings import settings

log = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_session_id(request: Request) -> str:
    """Extract the session ID from request state (set by middleware).

    Args:
        request: FastAPI request object with pre-assigned session state.

    Returns:
        str: Session ID as a string.

    Raises:
        UnauthorizedError: If the session ID was not set by middleware.
    """
    if not hasattr(request.state, "session_id"):
        log.warning("missing_session_id")
        raise UnauthorizedError("Missing session ID")
    return str(request.state.session_id)


async def get_current_user_id(
    token: str | None = Depends(oauth2_scheme),
) -> str:
    """Extract user_id from a JWT Bearer token."""
    if not token:
        raise UnauthorizedError("Missing authorization token")
    user_id = decode_token(token)
    if not user_id:
        raise UnauthorizedError("Invalid or expired token")
    return user_id


async def get_owner_id(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
) -> str:
    """Unified dependency: returns user_id (JWT) or session_id based on AUTH_REQUIRED.

    When AUTH_REQUIRED=True: requires a valid JWT Bearer token.
    When AUTH_REQUIRED=False: falls back to session_id from middleware.
    """
    if settings.AUTH_REQUIRED:
        return await get_current_user_id(token)
    return get_session_id(request)
