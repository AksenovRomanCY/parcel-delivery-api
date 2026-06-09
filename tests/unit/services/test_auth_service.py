"""Unit tests for authentication service behavior."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import BusinessError, UnauthorizedError
from app.core.security import hash_token
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services import auth as auth_module
from app.services.auth import AuthService


@pytest.mark.asyncio
async def test_register_creates_user_and_token(
    mock_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Registration should persist a user and return an access token."""
    # Arrange
    mock_session.scalar.return_value = None
    hash_password = MagicMock(return_value="hashed-password")
    create_access_token = MagicMock(return_value="access-token")
    create_refresh_token = MagicMock(return_value=("refresh-token", "refresh-jti"))
    create_csrf_token = MagicMock(return_value="csrf-token")
    monkeypatch.setattr(auth_module, "hash_password", hash_password)
    monkeypatch.setattr(auth_module, "create_access_token", create_access_token)
    monkeypatch.setattr(auth_module, "create_refresh_token", create_refresh_token)
    monkeypatch.setattr(auth_module, "create_csrf_token", create_csrf_token)
    service = AuthService(mock_session)

    # Act
    result = await service.register("user@example.com", "secret-password")

    # Assert
    user = result.user
    assert isinstance(user, User)
    assert user.email == "user@example.com"
    assert user.hashed_password == "hashed-password"
    assert result.access_token == "access-token"
    assert result.refresh_token == "refresh-token"
    assert result.csrf_token == "csrf-token"
    hash_password.assert_called_once_with("secret-password")
    assert mock_session.add.call_count == 2
    assert mock_session.add.call_args_list[0].args == (user,)
    assert mock_session.commit.await_count == 2
    mock_session.refresh.assert_awaited_once_with(user)
    create_access_token.assert_called_once_with(
        subject=user.id,
        role="user",
        scopes=("parcels:read", "parcels:write"),
    )
    create_refresh_token.assert_called_once_with()
    create_csrf_token.assert_called_once_with()


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(mock_session: AsyncMock) -> None:
    """Registration should reject an already registered email."""
    # Arrange
    mock_session.scalar.return_value = User(
        email="user@example.com",
        hashed_password="hashed-password",
    )
    service = AuthService(mock_session)

    # Act / Assert
    with pytest.raises(BusinessError, match="Email already registered"):
        await service.register("user@example.com", "secret-password")

    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_returns_user_and_token(
    mock_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Login should verify credentials and return an access token."""
    # Arrange
    user = User(email="user@example.com", hashed_password="hashed-password")
    mock_session.scalar.return_value = user
    verify_password = MagicMock(return_value=True)
    create_access_token = MagicMock(return_value="access-token")
    create_refresh_token = MagicMock(return_value=("refresh-token", "refresh-jti"))
    create_csrf_token = MagicMock(return_value="csrf-token")
    monkeypatch.setattr(auth_module, "verify_password", verify_password)
    monkeypatch.setattr(auth_module, "create_access_token", create_access_token)
    monkeypatch.setattr(auth_module, "create_refresh_token", create_refresh_token)
    monkeypatch.setattr(auth_module, "create_csrf_token", create_csrf_token)
    service = AuthService(mock_session)

    # Act
    result = await service.login("user@example.com", "secret-password")

    # Assert
    assert result.user == user
    assert result.access_token == "access-token"
    assert result.refresh_token == "refresh-token"
    assert result.csrf_token == "csrf-token"
    verify_password.assert_called_once_with("secret-password", "hashed-password")
    create_access_token.assert_called_once_with(
        subject=user.id,
        role="user",
        scopes=("parcels:read", "parcels:write"),
    )


@pytest.mark.parametrize(
    ("user", "password_matches"),
    [
        (None, False),
        (User(email="user@example.com", hashed_password="hashed-password"), False),
    ],
)
@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials(
    mock_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    user: User | None,
    password_matches: bool,
) -> None:
    """Login should reject missing users and wrong passwords."""
    # Arrange
    mock_session.scalar.return_value = user
    verify_password = MagicMock(return_value=password_matches)
    monkeypatch.setattr(auth_module, "verify_password", verify_password)
    service = AuthService(mock_session)

    # Act / Assert
    with pytest.raises(UnauthorizedError, match="Invalid email or password"):
        await service.login("user@example.com", "secret-password")

    if user is None:
        verify_password.assert_not_called()
    else:
        verify_password.assert_called_once_with("secret-password", "hashed-password")


@pytest.mark.asyncio
async def test_refresh_rotates_valid_token(
    mock_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refresh should revoke the old token and persist a replacement."""
    # Arrange
    old = RefreshToken(
        jti="old-jti",
        user_id="user-123",
        token_hash=hash_token("old-refresh"),
        family_id="family-123",
        expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    user = User(id="user-123", email="user@example.com", hashed_password="hash")
    mock_session.scalar.side_effect = [old, user]
    create_refresh_token = MagicMock(return_value=("new-refresh", "new-jti"))
    create_csrf_token = MagicMock(return_value="new-csrf")
    create_access_token = MagicMock(return_value="new-access")
    monkeypatch.setattr(auth_module, "create_refresh_token", create_refresh_token)
    monkeypatch.setattr(auth_module, "create_csrf_token", create_csrf_token)
    monkeypatch.setattr(auth_module, "create_access_token", create_access_token)
    service = AuthService(mock_session)

    # Act
    result = await service.refresh("old-refresh")

    # Assert
    assert result.user == user
    assert result.access_token == "new-access"
    assert result.refresh_token == "new-refresh"
    assert result.csrf_token == "new-csrf"
    assert old.revoked_at is not None
    assert old.replaced_by_jti == "new-jti"
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_reuse_revokes_family(mock_session: AsyncMock) -> None:
    """Refresh reuse should revoke the whole token family."""
    # Arrange
    old = RefreshToken(
        jti="old-jti",
        user_id="user-123",
        token_hash=hash_token("old-refresh"),
        family_id="family-123",
        expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        revoked_at=datetime.now(UTC).replace(tzinfo=None),
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    mock_session.scalar.return_value = old
    service = AuthService(mock_session)

    # Act / Assert
    with pytest.raises(UnauthorizedError, match="Invalid refresh token"):
        await service.refresh("old-refresh")

    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_rejects_expired_token(mock_session: AsyncMock) -> None:
    """Refresh should revoke an expired token before rejecting it."""
    # Arrange
    old = RefreshToken(
        jti="old-jti",
        user_id="user-123",
        token_hash=hash_token("old-refresh"),
        family_id="family-123",
        expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1),
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    mock_session.scalar.return_value = old
    service = AuthService(mock_session)

    # Act / Assert
    with pytest.raises(UnauthorizedError, match="Invalid refresh token"):
        await service.refresh("old-refresh")

    assert old.revoked_at is not None
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_rejects_token_for_missing_user(mock_session: AsyncMock) -> None:
    """Refresh should revoke a token whose owner no longer exists."""
    # Arrange
    old = RefreshToken(
        jti="old-jti",
        user_id="user-123",
        token_hash=hash_token("old-refresh"),
        family_id="family-123",
        expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    mock_session.scalar.side_effect = [old, None]
    service = AuthService(mock_session)

    # Act / Assert
    with pytest.raises(UnauthorizedError, match="Invalid refresh token"):
        await service.refresh("old-refresh")

    assert old.revoked_at is not None
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_logout_revokes_current_token(mock_session: AsyncMock) -> None:
    """Logout should mark the current refresh token as revoked."""
    # Arrange
    old = RefreshToken(
        jti="old-jti",
        user_id="user-123",
        token_hash=hash_token("old-refresh"),
        family_id="family-123",
        expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    mock_session.scalar.return_value = old
    service = AuthService(mock_session)

    # Act
    await service.logout("old-refresh")

    # Assert
    assert old.revoked_at is not None
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_logout_all_revokes_user_tokens(mock_session: AsyncMock) -> None:
    """Logout-all should issue a bulk revoke for the current user."""
    # Arrange
    service = AuthService(mock_session)

    # Act
    await service.logout_all("user-123")

    # Assert
    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_awaited_once()
