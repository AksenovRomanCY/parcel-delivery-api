"""Unit tests for custom OpenAPI security annotations."""

import pytest
from fastapi import FastAPI

from app.core.openapi import setup_custom_openapi
from app.core.settings import settings


def _sample_app() -> FastAPI:
    app = FastAPI(title="test", version="1.0")

    @app.post("/auth/login")
    async def login() -> dict[str, object]:
        return {}

    @app.get("/health")
    async def health() -> dict[str, object]:
        return {}

    @app.get("/metrics")
    async def metrics() -> dict[str, object]:
        return {}

    @app.post("/tasks/recalc-delivery")
    async def task() -> dict[str, object]:
        return {}

    @app.post("/parcels")
    async def parcels() -> dict[str, object]:
        return {}

    setup_custom_openapi(app)
    return app


def test_openapi_marks_public_admin_and_session_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAPI should assign public, admin, and session security by path."""
    # Arrange
    monkeypatch.setattr(settings, "AUTH_REQUIRED", False)

    # Act
    schema = _sample_app().openapi()

    # Assert
    schemes = schema["components"]["securitySchemes"]
    assert "SessionAuth" in schemes
    assert "AdminToken" in schemes
    assert "security" not in schema["paths"]["/auth/login"]["post"]
    assert "security" not in schema["paths"]["/health"]["get"]
    assert "security" not in schema["paths"]["/metrics"]["get"]
    assert schema["paths"]["/tasks/recalc-delivery"]["post"]["security"] == [
        {"AdminToken": []}
    ]
    assert schema["paths"]["/parcels"]["post"]["security"] == [{"SessionAuth": []}]


def test_openapi_uses_bearer_auth_when_auth_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAPI should use bearer auth for domain routes in JWT mode."""
    # Arrange
    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)

    # Act
    schema = _sample_app().openapi()

    # Assert
    assert "BearerAuth" in schema["components"]["securitySchemes"]
    assert schema["paths"]["/parcels"]["post"]["security"] == [{"BearerAuth": []}]
