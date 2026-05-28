"""Authentication service: registration and login.

This service owns credential persistence and token issuance so routers never
handle password hashes or JWT construction directly.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User

log = logging.getLogger(__name__)


class AuthService:
    """Coordinate user registration, password checks, and token issuance."""

    def __init__(self, session: AsyncSession) -> None:
        """Create the service with a request-scoped database session."""
        self.session = session

    async def register(self, email: str, password: str) -> tuple[User, str]:
        """Register a new user and return the user with an access token.

        Duplicate email checks happen before hashing to fail fast and return a
        business error that the API layer maps to HTTP 400.
        """
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
        """Authenticate a user and return the user with an access token.

        Both unknown emails and wrong passwords produce the same error message
        so callers cannot enumerate registered accounts.
        """
        user = await self.session.scalar(select(User).where(User.email == email))
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")

        token = create_access_token(subject=user.id)
        log.info("user_logged_in: user_id=%s", user.id)
        return user, token
