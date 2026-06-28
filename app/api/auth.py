"""Authentication endpoints: register/login, refresh rotation, and logout."""

import logging
from secrets import compare_digest

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.api.examples import (
    FORBIDDEN_ERROR_EXAMPLE,
    TOKEN_RESPONSE_EXAMPLE,
    UNAUTHORIZED_ERROR_EXAMPLE,
    VALIDATION_ERROR_EXAMPLE,
)
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.rate_limit import limiter
from app.core.settings import settings
from app.db.deps import get_db
from app.schemas import ErrorResponse
from app.schemas.auth import TokenResponse, UserLogin, UserRegister
from app.services.auth import AuthResult, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

log = logging.getLogger(__name__)


def _cookie_secure() -> bool:
    """Return whether auth cookies should be marked Secure."""
    return settings.ENVIRONMENT == "prod"


def _cookie_max_age() -> int:
    """Return refresh-cookie lifetime in seconds."""
    return settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


def _set_auth_cookies(response: Response, result: AuthResult) -> None:
    """Set refresh and CSRF cookies for a successful auth response."""
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        result.refresh_token,
        max_age=_cookie_max_age(),
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/auth",
    )
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        result.csrf_token,
        max_age=_cookie_max_age(),
        httponly=False,
        secure=_cookie_secure(),
        samesite="lax",
        path="/auth",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear refresh and CSRF cookies."""
    response.delete_cookie(settings.REFRESH_COOKIE_NAME, path="/auth")
    response.delete_cookie(settings.CSRF_COOKIE_NAME, path="/auth")


def _refresh_token_from_request(request: Request) -> str:
    token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not token:
        raise UnauthorizedError("Missing refresh token")
    return token


def _require_csrf(request: Request) -> None:
    csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)
    csrf_header = request.headers.get(settings.CSRF_HEADER_NAME)
    if (
        not csrf_cookie
        or not csrf_header
        or not compare_digest(csrf_cookie, csrf_header)
    ):
        raise ForbiddenError("Invalid CSRF token")


@router.post(
    "/register",
    status_code=201,
    response_model=TokenResponse,
    responses={
        201: {
            "description": "User registered and access token issued.",
            "content": {"application/json": {"example": TOKEN_RESPONSE_EXAMPLE}},
        },
        400: {
            "model": ErrorResponse,
            "description": "Email is already registered.",
            "content": {
                "application/json": {
                    "example": {
                        "code": "business_error",
                        "message": "Email already registered",
                        "details": None,
                    }
                }
            },
        },
        422: {
            "model": ErrorResponse,
            "description": "Invalid registration payload.",
            "content": {"application/json": {"example": VALIDATION_ERROR_EXAMPLE}},
        },
    },
)
@limiter.limit("10/minute")
async def register(
    request: Request,
    response: Response,
    body: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user and return a JWT access token."""
    result = await AuthService(db).register(body.email, body.password)
    _set_auth_cookies(response, result)
    return TokenResponse(access_token=result.access_token)


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        200: {
            "description": "User authenticated and access token issued.",
            "content": {"application/json": {"example": TOKEN_RESPONSE_EXAMPLE}},
        },
        401: {
            "model": ErrorResponse,
            "description": "Invalid email or password.",
            "content": {"application/json": {"example": UNAUTHORIZED_ERROR_EXAMPLE}},
        },
        422: {
            "model": ErrorResponse,
            "description": "Invalid login payload.",
            "content": {"application/json": {"example": VALIDATION_ERROR_EXAMPLE}},
        },
    },
)
@limiter.limit("20/minute")
async def login(
    request: Request,
    response: Response,
    body: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and return a JWT access token."""
    result = await AuthService(db).login(body.email, body.password)
    _set_auth_cookies(response, result)
    return TokenResponse(access_token=result.access_token)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        200: {
            "description": "Refresh token rotated and access token issued.",
            "content": {"application/json": {"example": TOKEN_RESPONSE_EXAMPLE}},
        },
        401: {
            "model": ErrorResponse,
            "description": "Missing, expired, or revoked refresh token.",
            "content": {"application/json": {"example": UNAUTHORIZED_ERROR_EXAMPLE}},
        },
        403: {
            "model": ErrorResponse,
            "description": "Missing or invalid CSRF token.",
            "content": {"application/json": {"example": FORBIDDEN_ERROR_EXAMPLE}},
        },
    },
)
@limiter.limit("20/minute")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Rotate a refresh token and return a new access token."""
    _require_csrf(request)
    result = await AuthService(db).refresh(_refresh_token_from_request(request))
    _set_auth_cookies(response, result)
    return TokenResponse(access_token=result.access_token)


@router.post(
    "/logout",
    status_code=204,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Missing refresh token.",
            "content": {"application/json": {"example": UNAUTHORIZED_ERROR_EXAMPLE}},
        },
        403: {
            "model": ErrorResponse,
            "description": "Missing or invalid CSRF token.",
            "content": {"application/json": {"example": FORBIDDEN_ERROR_EXAMPLE}},
        },
    },
)
@limiter.limit("20/minute")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Revoke the current refresh token and clear auth cookies."""
    _require_csrf(request)
    await AuthService(db).logout(_refresh_token_from_request(request))
    _clear_auth_cookies(response)
    response.status_code = 204
    return response


@router.post(
    "/logout-all",
    status_code=204,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Missing or invalid access token.",
            "content": {"application/json": {"example": UNAUTHORIZED_ERROR_EXAMPLE}},
        },
    },
)
@limiter.limit("10/minute")
async def logout_all(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Response:
    """Revoke all refresh tokens for the current user and clear auth cookies."""
    await AuthService(db).logout_all(user_id)
    _clear_auth_cookies(response)
    response.status_code = 204
    return response
