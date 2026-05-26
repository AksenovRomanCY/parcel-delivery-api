"""Authentication request and response schemas."""

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Payload accepted by the registration endpoint."""

    email: EmailStr = Field(..., examples=["user@example.com"])
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Payload accepted by the login endpoint."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Bearer token returned after successful authentication."""

    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    """Public user representation safe to return from API handlers."""

    id: str
    email: str

    model_config = {"from_attributes": True}
