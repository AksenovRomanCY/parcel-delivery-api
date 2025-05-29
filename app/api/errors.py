"""Custom exception handlers for FastAPI.

Handles validation errors, business logic violations, and not-found
scenarios with consistent JSON error structure.
"""

import logging
from collections.abc import Sequence
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    BusinessError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from app.main import app

log = logging.getLogger(__name__)


def _error_response(
    code: str,
    message: str,
    details: Sequence[dict[str, Any]] | None = None,
    *,
    status: int = 400,
    exc: Exception | None = None,
) -> JSONResponse:
    """Return a structured JSON error response and log it.

    Args:
        code: Machine-readable error identifier.
        message: Human-readable explanation of the error.
        details: Optional list of structured error details (e.g. from Pydantic).
        status: HTTP status code to return.
        exc: Optional exception object for structured logging.

    Returns:
        JSONResponse: Response with error payload.
    """
    log.warning(
        "api_error: code=%s message=%s status=%s details=%s",
        code,
        message,
        status,
        details,
        exc_info=exc,
    )

    return JSONResponse(
        status_code=status,
        content={"code": code, "message": message, "details": details},
    )


@app.exception_handler(Exception)
async def internal_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected uncaught exceptions (500 Internal Server Error).

    Args:
        _request: The request that triggered the exception.
        exc: The original uncaught exception.

    Returns:
        JSONResponse: Generic error response with code ``internal_error``.
    """
    return _error_response(
        "internal_error", "Unexpected server error", None, status=500, exc=exc
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle 422 Unprocessable Entity from request body validation.

    Triggered by malformed input that fails Pydantic validation.

    Args:
        _request: The request that triggered the error.
        exc: The raised validation exception.

    Returns:
        JSONResponse: Error with code ``validation_error`` and details.
    """
    return _error_response(
        "validation_error",
        "Payload validation failed",
        exc.errors(),
        status=422,
    )


@app.exception_handler(BusinessError)
async def business_error_handler(_request: Request, exc: BusinessError) -> JSONResponse:
    """Handle 400 Bad Request when business rules are violated.

    Args:
        _request: The request that triggered the error.
        exc: Raised custom exception with user-facing message.

    Returns:
        JSONResponse: Error with code ``business_error``.
    """
    return _error_response("business_error", str(exc), None, status=400)


@app.exception_handler(NotFoundError)
async def not_found_error_handler(
    _request: Request, exc: NotFoundError
) -> JSONResponse:
    """Handle 404 Not Found for missing or unauthorized resources.

    Used when a resource is not found or belongs to another session.

    Args:
        _request: The request that triggered the error.
        exc: Raised custom NotFoundError.

    Returns:
        JSONResponse: Error with code ``not_found``.
    """
    return _error_response("not_found", str(exc), None, status=404)


@app.exception_handler(UnauthorizedError)
async def unauthorized_error_handler(
    _request: Request, exc: UnauthorizedError
) -> JSONResponse:
    """Handle 401 Unauthorized for missing or invalid authentication.

    Args:
        _request: The request that triggered the error.
        exc: Raised UnauthorizedError.

    Returns:
        JSONResponse: Error with code ``unauthorized``.
    """
    return _error_response("unauthorized", str(exc), None, status=401)


@app.exception_handler(ForbiddenError)
async def forbidden_error_handler(
    _request: Request, exc: ForbiddenError
) -> JSONResponse:
    """Handle 403 Forbidden for unauthorized access to a valid resource.

    Args:
        _request: The request that triggered the error.
        exc: Raised ForbiddenError.

    Returns:
        JSONResponse: Error with code ``forbidden``.
    """
    return _error_response("forbidden", str(exc), None, status=403)
