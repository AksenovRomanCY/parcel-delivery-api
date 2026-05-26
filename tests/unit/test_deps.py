"""Unit tests for request ownership dependencies."""

import pytest
from starlette.requests import Request

from app.api.deps import get_owner_id, require_task_admin_token
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import create_access_token
from app.core.settings import settings


def _request_with_session(session_id: str) -> Request:
    request = Request({"type": "http", "headers": []})
    request.state.session_id = session_id
    return request


@pytest.mark.asyncio
async def test_get_owner_id_returns_session_when_auth_not_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Owner dependency should return session ID in legacy mode."""
    monkeypatch.setattr(settings, "AUTH_REQUIRED", False)

    owner_id = await get_owner_id(_request_with_session("session-123"), token=None)

    assert owner_id == "session-123"


@pytest.mark.asyncio
async def test_get_owner_id_returns_jwt_subject_when_auth_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Owner dependency should return JWT subject in auth-required mode."""
    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)
    token = create_access_token("user-123")

    owner_id = await get_owner_id(_request_with_session("session-123"), token=token)

    assert owner_id == "user-123"


@pytest.mark.asyncio
async def test_get_owner_id_requires_token_when_auth_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Owner dependency should reject missing bearer token in JWT mode."""
    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)

    with pytest.raises(UnauthorizedError, match="Missing authorization token"):
        await get_owner_id(_request_with_session("session-123"), token=None)


def test_require_task_admin_token_accepts_configured_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task admin guard should accept the configured token."""
    monkeypatch.setattr(settings, "TASK_ADMIN_TOKEN", "test-admin-token")

    require_task_admin_token("test-admin-token")


def test_require_task_admin_token_rejects_missing_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task admin guard should reject a missing token."""
    monkeypatch.setattr(settings, "TASK_ADMIN_TOKEN", "test-admin-token")

    with pytest.raises(ForbiddenError, match="Invalid admin token"):
        require_task_admin_token(None)


def test_require_task_admin_token_rejects_wrong_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task admin guard should reject the wrong token."""
    monkeypatch.setattr(settings, "TASK_ADMIN_TOKEN", "test-admin-token")

    with pytest.raises(ForbiddenError, match="Invalid admin token"):
        require_task_admin_token("wrong-token")


def test_require_task_admin_token_rejects_empty_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task admin guard should reject requests when token config is empty."""
    monkeypatch.setattr(settings, "TASK_ADMIN_TOKEN", "")

    with pytest.raises(ForbiddenError, match="Manual task trigger is disabled"):
        require_task_admin_token("test-admin-token")
