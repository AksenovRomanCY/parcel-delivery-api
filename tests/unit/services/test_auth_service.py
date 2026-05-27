"""Unit tests for authentication service behavior."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import BusinessError, UnauthorizedError
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
    monkeypatch.setattr(auth_module, "hash_password", hash_password)
    monkeypatch.setattr(auth_module, "create_access_token", create_access_token)
    service = AuthService(mock_session)

    # Act
    user, token = await service.register("user@example.com", "secret-password")

    # Assert
    assert isinstance(user, User)
    assert user.email == "user@example.com"
    assert user.hashed_password == "hashed-password"
    assert token == "access-token"
    hash_password.assert_called_once_with("secret-password")
    mock_session.add.assert_called_once_with(user)
    mock_session.commit.assert_awaited_once_with()
    mock_session.refresh.assert_awaited_once_with(user)
    create_access_token.assert_called_once_with(subject=user.id)


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
    monkeypatch.setattr(auth_module, "verify_password", verify_password)
    monkeypatch.setattr(auth_module, "create_access_token", create_access_token)
    service = AuthService(mock_session)

    # Act
    result_user, token = await service.login("user@example.com", "secret-password")

    # Assert
    assert result_user == user
    assert token == "access-token"
    verify_password.assert_called_once_with("secret-password", "hashed-password")
    create_access_token.assert_called_once_with(subject=user.id)


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
