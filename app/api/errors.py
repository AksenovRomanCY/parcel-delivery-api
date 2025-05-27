from collections.abc import Sequence
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.main import app


def _error_response(
    code: str,
    message: str,
    details: Sequence[dict[str, Any]] | None = None,
    *,
    status: int = 400,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"code": code, "message": message, "details": details},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return _error_response(
        "validation_error",
        "Payload validation failed",
        exc.errors(),
        status=422,
    )


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
    return _error_response("value_error", str(exc), None, status=400)
