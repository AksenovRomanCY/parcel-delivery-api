"""Unit tests for request ownership dependencies."""

from collections.abc import Callable

import pytest
from starlette.requests import Request

from app.api.deps import get_owner_id, require_task_admin_token
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import create_access_token
from app.core.settings import settings

RequestFactory = Callable[..., Request]


def _request_with_session(request_factory: RequestFactory, session_id: str) -> Request:
    request = request_factory()
    request.state.session_id = session_id
    return request


@pytest.mark.asyncio
async def test_get_owner_id_returns_session_when_auth_not_required(
    monkeypatch: pytest.MonkeyPatch,
    request_factory: RequestFactory,
) -> None:
    """Owner dependency should return session ID in legacy mode."""
    # Arrange
    monkeypatch.setattr(settings, "AUTH_REQUIRED", False)
    request = _request_with_session(request_factory, "session-123")

    # Act
    owner_id = await get_owner_id(request, token=None)

    # Assert
    assert owner_id == "session-123"


@pytest.mark.asyncio
async def test_get_owner_id_returns_jwt_subject_when_auth_required(
    monkeypatch: pytest.MonkeyPatch,
    request_factory: RequestFactory,
) -> None:
    """Owner dependency should return JWT subject in auth-required mode."""
    # Arrange
    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)
    token = create_access_token("user-123")
    request = _request_with_session(request_factory, "session-123")

    # Act
    owner_id = await get_owner_id(request, token=token)

    # Assert
    assert owner_id == "user-123"


@pytest.mark.asyncio
async def test_get_owner_id_requires_token_when_auth_required(
    monkeypatch: pytest.MonkeyPatch,
    request_factory: RequestFactory,
) -> None:
    """Owner dependency should reject missing bearer token in JWT mode."""
    # Arrange
    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)
    request = _request_with_session(request_factory, "session-123")

    # Act / Assert
    with pytest.raises(UnauthorizedError, match="Missing authorization token"):
        await get_owner_id(request, token=None)


@pytest.mark.asyncio
async def test_get_owner_id_rejects_missing_required_scope(
    monkeypatch: pytest.MonkeyPatch,
    request_factory: RequestFactory,
) -> None:
    """Owner dependency should reject JWTs without the required scope."""
    # Arrange
    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)
    token = create_access_token("user-123", scopes=("parcels:read",))
    request = _request_with_session(request_factory, "session-123")

    # Act / Assert
    with pytest.raises(UnauthorizedError, match="Invalid or expired token"):
        await get_owner_id(
            request,
            token=token,
            required_scopes=("parcels:write",),
        )


def test_require_task_admin_token_accepts_configured_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task admin guard should accept the configured token."""
    # Arrange
    monkeypatch.setattr(settings, "TASK_ADMIN_TOKEN", "test-admin-token")

    # Act
    require_task_admin_token("test-admin-token")

    # Assert
    # No exception is the assertion for this guard.


@pytest.mark.parametrize("token", [None, "wrong-token"])
def test_require_task_admin_token_rejects_invalid_token(
    monkeypatch: pytest.MonkeyPatch,
    token: str | None,
) -> None:
    """Task admin guard should reject missing or wrong tokens."""
    # Arrange
    monkeypatch.setattr(settings, "TASK_ADMIN_TOKEN", "test-admin-token")

    # Act / Assert
    with pytest.raises(ForbiddenError, match="Invalid admin token"):
        require_task_admin_token(token)


def test_require_task_admin_token_rejects_empty_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task admin guard should reject requests when token config is empty."""
    # Arrange
    monkeypatch.setattr(settings, "TASK_ADMIN_TOKEN", "")

    # Act / Assert
    with pytest.raises(ForbiddenError, match="Manual task trigger is disabled"):
        require_task_admin_token("test-admin-token")
