"""Authentication endpoints: register and login.

These routes issue JWTs used when ``AUTH_REQUIRED=True``. They remain mounted
in legacy session mode as well, which keeps local testing and gradual migration
between ownership modes straightforward.
"""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.db.deps import get_db
from app.schemas.auth import TokenResponse, UserLogin, UserRegister
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

log = logging.getLogger(__name__)


@router.post("/register", status_code=201, response_model=TokenResponse)
@limiter.limit("10/minute")
async def register(
    request: Request,
    body: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user and return a JWT access token.

    The service owns duplicate-email checks and password hashing; the route only
    maps the validated request body to that service call.
    """
    _user, token = await AuthService(db).register(body.email, body.password)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
async def login(
    request: Request,
    body: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and return a JWT access token.

    Failed credential checks are raised as domain auth errors and formatted by
    the shared exception handlers.
    """
    _user, token = await AuthService(db).login(body.email, body.password)
    return TokenResponse(access_token=token)
