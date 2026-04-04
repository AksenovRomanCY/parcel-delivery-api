"""Custom exception handlers for FastAPI.

Handles validation errors, business logic violations, and not-found
scenarios with consistent JSON error structure.
"""

import logging
from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    BusinessError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)

log = logging.getLogger(__name__)


def _error_response(
    code: str,
    message: str,
    details: Sequence[dict[str, Any]] | None = None,
    *,
    status: int = 400,
    exc: Exception | None = None,
) -> JSONResponse:
    """Return a structured JSON error response and log it."""
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


async def internal_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    return _error_response(
        "internal_error", "Unexpected server error", None, status=500, exc=exc
    )


async def validation_exception_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return _error_response(
        "validation_error",
        "Payload validation failed",
        exc.errors(),
        status=422,
    )


async def business_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    return _error_response("business_error", str(exc), None, status=400)


async def not_found_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    return _error_response("not_found", str(exc), None, status=404)


async def unauthorized_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    return _error_response("unauthorized", str(exc), None, status=401)


async def forbidden_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    return _error_response("forbidden", str(exc), None, status=403)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI app."""
    app.add_exception_handler(Exception, internal_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(BusinessError, business_error_handler)
    app.add_exception_handler(NotFoundError, not_found_error_handler)
    app.add_exception_handler(UnauthorizedError, unauthorized_error_handler)
    app.add_exception_handler(ForbiddenError, forbidden_error_handler)
