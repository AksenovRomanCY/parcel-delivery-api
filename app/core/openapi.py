"""OpenAPI schema customization for auth hints and operational endpoints."""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.core.settings import settings

PUBLIC_PATH_PREFIXES = ("/auth", "/health", "/metrics")
ADMIN_PATH_PREFIXES = ("/tasks",)


def _is_operation(value: object) -> bool:
    return isinstance(value, dict) and "responses" in value


def _auth_scheme_name() -> str:
    return "BearerAuth" if settings.AUTH_REQUIRED else "SessionAuth"


def setup_custom_openapi(app: FastAPI) -> None:
    """Inject custom OpenAPI schema with the appropriate security scheme.

    When AUTH_REQUIRED=True: uses BearerAuth (JWT).
    When AUTH_REQUIRED=False: uses SessionAuth (X-Session-Id header).
    """

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,  # noqa
            version=app.version,  # noqa
            description=app.description,  # noqa
            routes=app.routes,
        )

        components = schema.setdefault("components", {})
        security_schemes = components.setdefault("securitySchemes", {})

        if settings.AUTH_REQUIRED:
            security_schemes.update(
                {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                    }
                }
            )
        else:
            security_schemes.update(
                {
                    "SessionAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-Session-Id",
                    }
                }
            )

        security_schemes.update(
            {
                "AdminToken": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-Admin-Token",
                }
            }
        )

        # Security is assigned by path group so Swagger mirrors runtime behavior:
        # auth/health/metrics are public, task routes use an ops token, and
        # domain routes use either session or JWT ownership.
        for path_name, path_item in schema.get("paths", {}).items():
            if path_name.startswith(PUBLIC_PATH_PREFIXES):
                continue

            if path_name.startswith(ADMIN_PATH_PREFIXES):
                security: dict[str, list[Any]] = {"AdminToken": []}
            else:
                security = {_auth_scheme_name(): []}

            for method in path_item.values():
                if _is_operation(method):
                    method.setdefault("security", []).append(security)

        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
