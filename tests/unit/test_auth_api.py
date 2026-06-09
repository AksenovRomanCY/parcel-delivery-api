"""Unit tests for authentication router helpers."""

from collections.abc import Callable

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.api import auth as auth_api
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.settings import settings
from app.models.user import User
from app.services.auth import AuthResult

RequestFactory = Callable[..., Request]


def _set_cookie_headers(response: Response) -> list[str]:
    return [
        value.decode() for name, value in response.raw_headers if name == b"set-cookie"
    ]


def test_set_auth_cookies_sets_refresh_http_only_and_readable_csrf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful auth should set a protected refresh cookie and readable CSRF."""
    # Arrange
    monkeypatch.setattr(settings, "ENVIRONMENT", "prod")
    response = Response()
    result = AuthResult(
        user=User(id="user-123", email="user@example.com", hashed_password="hash"),
        access_token="access-token",
        refresh_token="refresh-token",
        csrf_token="csrf-token",
    )

    # Act
    auth_api._set_auth_cookies(response, result)

    # Assert
    headers = _set_cookie_headers(response)
    assert len(headers) == 2
    assert any(
        header.startswith(f"{settings.REFRESH_COOKIE_NAME}=refresh-token")
        and "HttpOnly" in header
        and "Secure" in header
        and "Path=/auth" in header
        for header in headers
    )
    assert any(
        header.startswith(f"{settings.CSRF_COOKIE_NAME}=csrf-token")
        and "HttpOnly" not in header
        and "Secure" in header
        and "Path=/auth" in header
        for header in headers
    )


def test_clear_auth_cookies_expires_refresh_and_csrf_cookies() -> None:
    """Logout responses should expire both auth cookies."""
    # Arrange
    response = Response()

    # Act
    auth_api._clear_auth_cookies(response)

    # Assert
    headers = _set_cookie_headers(response)
    assert len(headers) == 2
    assert all("Max-Age=0" in header for header in headers)
    assert all("Path=/auth" in header for header in headers)


def test_refresh_token_from_request_reads_configured_cookie(
    request_factory: RequestFactory,
) -> None:
    """Refresh token helper should read the configured cookie name."""
    # Arrange
    request = request_factory(
        path="/auth/refresh",
        headers=[(b"cookie", f"{settings.REFRESH_COOKIE_NAME}=token-123".encode())],
    )

    # Act
    token = auth_api._refresh_token_from_request(request)

    # Assert
    assert token == "token-123"


def test_refresh_token_from_request_rejects_missing_cookie(
    request_factory: RequestFactory,
) -> None:
    """Refresh token helper should reject requests without a refresh cookie."""
    # Arrange
    request = request_factory(path="/auth/refresh")

    # Act / Assert
    with pytest.raises(UnauthorizedError, match="Missing refresh token"):
        auth_api._refresh_token_from_request(request)


def test_require_csrf_accepts_matching_cookie_and_header(
    request_factory: RequestFactory,
) -> None:
    """CSRF guard should accept matching cookie/header values."""
    # Arrange
    request = request_factory(
        path="/auth/refresh",
        headers=[
            (b"cookie", f"{settings.CSRF_COOKIE_NAME}=csrf-123".encode()),
            (settings.CSRF_HEADER_NAME.lower().encode(), b"csrf-123"),
        ],
    )

    # Act
    auth_api._require_csrf(request)

    # Assert
    # No exception is the assertion.


@pytest.mark.parametrize(
    "headers",
    [
        [],
        [(b"cookie", f"{settings.CSRF_COOKIE_NAME}=csrf-123".encode())],
        [
            (b"cookie", f"{settings.CSRF_COOKIE_NAME}=csrf-123".encode()),
            (settings.CSRF_HEADER_NAME.lower().encode(), b"wrong"),
        ],
    ],
)
def test_require_csrf_rejects_missing_or_mismatched_tokens(
    request_factory: RequestFactory,
    headers: list[tuple[bytes, bytes]],
) -> None:
    """CSRF guard should reject missing or mismatched tokens."""
    # Arrange
    request = request_factory(path="/auth/refresh", headers=headers)

    # Act / Assert
    with pytest.raises(ForbiddenError, match="Invalid CSRF token"):
        auth_api._require_csrf(request)
