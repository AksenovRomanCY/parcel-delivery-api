"""FastAPI dependencies shared by route handlers.

The main idea here is `owner_id`: parcel routes should not care whether the
caller is represented by a legacy session UUID or by an authenticated user ID.
That mode switch is centralized in `get_owner_id`.
"""

import logging
from collections.abc import Iterable
from secrets import compare_digest

from fastapi import Depends, Header, Request
from fastapi.security import OAuth2PasswordBearer

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import TokenClaims, decode_token
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
    """Extract the user ID from a JWT Bearer token.

    Returns:
        User ID stored in the token ``sub`` claim.

    Raises:
        UnauthorizedError: If the token is missing, invalid, or expired.
    """
    if not token:
        raise UnauthorizedError("Missing authorization token")
    claims = decode_token(token)
    if claims is None:
        raise UnauthorizedError("Invalid or expired token")
    return claims.sub


async def get_current_claims(
    token: str | None = Depends(oauth2_scheme),
) -> TokenClaims:
    """Return validated JWT claims for the current Bearer token."""
    if not token:
        raise UnauthorizedError("Missing authorization token")
    claims = decode_token(token)
    if claims is None:
        raise UnauthorizedError("Invalid or expired token")
    return claims


async def get_owner_id(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    required_scopes: Iterable[str] = (),
) -> str:
    """Return the ownership key used by parcel services.

    When AUTH_REQUIRED=True: requires a valid JWT Bearer token.
    When AUTH_REQUIRED=False: falls back to session_id from middleware.
    """
    if settings.AUTH_REQUIRED:
        # JWT mode stores parcel ownership in Parcel.user_id and requires a
        # Bearer token for every protected parcel operation.
        if not token:
            raise UnauthorizedError("Missing authorization token")
        claims = decode_token(token, required_scopes=required_scopes)
        if claims is None:
            raise UnauthorizedError("Invalid or expired token")
        return claims.sub
    # Legacy mode stores parcel ownership in Parcel.session_id and relies on
    # session middleware to create/propagate X-Session-Id.
    return get_session_id(request)


async def get_parcel_reader_owner_id(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
) -> str:
    """Return owner ID for parcel read endpoints with read-scope enforcement."""
    return await get_owner_id(request, token, required_scopes=("parcels:read",))


async def get_parcel_writer_owner_id(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
) -> str:
    """Return owner ID for parcel write endpoints with write-scope enforcement."""
    return await get_owner_id(request, token, required_scopes=("parcels:write",))


def require_task_admin_token(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> None:
    """Require the operational shared secret for manual task endpoints.

    This is intentionally separate from user JWT auth: the endpoint triggers
    process-wide background work and should be operated by infrastructure/admin
    tooling. Leaving TASK_ADMIN_TOKEN empty disables manual triggers.
    """
    if not settings.TASK_ADMIN_TOKEN:
        raise ForbiddenError("Manual task trigger is disabled")
    if not x_admin_token or not compare_digest(
        x_admin_token, settings.TASK_ADMIN_TOKEN
    ):
        raise ForbiddenError("Invalid admin token")
