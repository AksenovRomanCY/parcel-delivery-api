"""Authentication service: registration, login, refresh rotation, and logout.

This service owns credential persistence and token issuance so routers never
handle password hashes, refresh token hashes, or JWT construction directly.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError, UnauthorizedError
from app.core.security import (
    DEFAULT_USER_ROLE,
    DEFAULT_USER_SCOPES,
    create_access_token,
    create_csrf_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.core.settings import settings
from app.models.refresh_token import RefreshToken
from app.models.user import User

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthResult:
    """Tokens returned after login, registration, or refresh rotation."""

    user: User
    access_token: str
    refresh_token: str
    csrf_token: str


class AuthService:
    """Coordinate users, password checks, access JWTs, and refresh tokens."""

    def __init__(self, session: AsyncSession) -> None:
        """Create the service with a request-scoped database session."""
        self.session = session

    async def register(self, email: str, password: str) -> AuthResult:
        """Register a new user and return access/refresh credentials."""
        existing = await self.session.scalar(select(User).where(User.email == email))
        if existing:
            raise BusinessError("Email already registered")

        user = User(email=email, hashed_password=hash_password(password))
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        result = await self._issue_tokens(user)
        log.info("user_registered: user_id=%s", user.id)
        return result

    async def login(self, email: str, password: str) -> AuthResult:
        """Authenticate a user and return access/refresh credentials."""
        user = await self.session.scalar(select(User).where(User.email == email))
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")

        result = await self._issue_tokens(user)
        log.info("user_logged_in: user_id=%s", user.id)
        return result

    async def refresh(self, raw_refresh_token: str) -> AuthResult:
        """Rotate a valid refresh token and return a new credential set."""
        token = await self._get_refresh_token(raw_refresh_token)
        now = self._now()

        if token.revoked_at is not None:
            await self._revoke_family(token.family_id, now)
            await self.session.commit()
            raise UnauthorizedError("Invalid refresh token")

        if token.expires_at <= now:
            token.revoked_at = now
            await self.session.commit()
            raise UnauthorizedError("Invalid refresh token")

        user = await self.session.scalar(select(User).where(User.id == token.user_id))
        if user is None:
            token.revoked_at = now
            await self.session.commit()
            raise UnauthorizedError("Invalid refresh token")

        raw_token, jti = create_refresh_token()
        csrf_token = create_csrf_token()
        token.revoked_at = now
        token.replaced_by_jti = jti
        self.session.add(
            RefreshToken(
                jti=jti,
                user_id=user.id,
                token_hash=hash_token(raw_token),
                family_id=token.family_id,
                expires_at=self._refresh_expires_at(now),
                created_at=now,
            )
        )
        await self.session.commit()

        log.info(
            "refresh_token_rotated: user_id=%s family_id=%s",
            user.id,
            token.family_id,
        )
        return AuthResult(
            user=user,
            access_token=self._create_user_access_token(user),
            refresh_token=raw_token,
            csrf_token=csrf_token,
        )

    async def logout(self, raw_refresh_token: str) -> None:
        """Revoke the current refresh token."""
        token = await self._get_refresh_token(raw_refresh_token)
        if token.revoked_at is None:
            token.revoked_at = self._now()
            await self.session.commit()
        log.info("refresh_token_revoked: user_id=%s jti=%s", token.user_id, token.jti)

    async def logout_all(self, user_id: str) -> None:
        """Revoke all refresh tokens for a user."""
        now = self._now()
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .where(RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await self.session.commit()
        log.info("all_refresh_tokens_revoked: user_id=%s", user_id)

    async def _issue_tokens(self, user: User) -> AuthResult:
        """Create and persist a new refresh token family for a user."""
        now = self._now()
        raw_token, jti = create_refresh_token()
        csrf_token = create_csrf_token()
        family_id = str(uuid4())
        self.session.add(
            RefreshToken(
                jti=jti,
                user_id=user.id,
                token_hash=hash_token(raw_token),
                family_id=family_id,
                expires_at=self._refresh_expires_at(now),
                created_at=now,
            )
        )
        await self.session.commit()
        return AuthResult(
            user=user,
            access_token=self._create_user_access_token(user),
            refresh_token=raw_token,
            csrf_token=csrf_token,
        )

    async def _get_refresh_token(self, raw_refresh_token: str) -> RefreshToken:
        token = await self.session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_token(raw_refresh_token)
            )
        )
        if token is None:
            raise UnauthorizedError("Invalid refresh token")
        return token

    async def _revoke_family(self, family_id: str, revoked_at: datetime) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id)
            .where(RefreshToken.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )

    def _create_user_access_token(self, user: User) -> str:
        return create_access_token(
            subject=user.id,
            role=user.role or DEFAULT_USER_ROLE,
            scopes=DEFAULT_USER_SCOPES,
        )

    def _refresh_expires_at(self, now: datetime) -> datetime:
        return now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    def _now(self) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)
