"""Authentication request and response schemas.

These schemas are deliberately small because auth behavior lives in
``AuthService`` and token helpers. Keeping request/response shapes minimal
makes auth routes easy to consume from Swagger UI and integration tests.
"""

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Payload accepted by the registration endpoint.

    Email is validated by Pydantic and password length bounds prevent obviously
    unusable credentials before service-level duplicate checks run.
    """

    email: EmailStr = Field(..., examples=["user@example.com"])
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Payload accepted by the login endpoint."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Bearer token returned after successful authentication.

    ``token_type`` follows the OAuth2 bearer convention used by FastAPI's
    Swagger authorization UI.
    """

    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    """Public user representation safe to return from API handlers."""

    id: str
    email: str

    model_config = {"from_attributes": True}
