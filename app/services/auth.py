"""Authentication service: registration and login."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User

log = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register(self, email: str, password: str) -> tuple[User, str]:
        """Register a new user and return the user with an access token."""
        existing = await self.session.scalar(select(User).where(User.email == email))
        if existing:
            raise BusinessError("Email already registered")

        user = User(email=email, hashed_password=hash_password(password))
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        token = create_access_token(subject=user.id)
        log.info("user_registered: user_id=%s", user.id)
        return user, token

    async def login(self, email: str, password: str) -> tuple[User, str]:
        """Authenticate a user and return the user with an access token."""
        user = await self.session.scalar(select(User).where(User.email == email))
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")

        token = create_access_token(subject=user.id)
        log.info("user_logged_in: user_id=%s", user.id)
        return user, token
