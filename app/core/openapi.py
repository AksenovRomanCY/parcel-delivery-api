"""OpenAPI schema customization for auth hints and operational endpoints."""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.core.settings import settings

PUBLIC_PATH_PREFIXES = ("/auth", "/health", "/metrics", "/parcel-types")
ADMIN_PATH_PREFIXES = ("/tasks",)
JWT_PATH_PREFIXES = ("/auth/logout-all",)


def _is_operation(value: object) -> bool:
    """Return True when an OpenAPI path item value is an HTTP operation.

    OpenAPI path objects also contain metadata-like keys, so callers need this
    guard before mutating method-specific security configuration.
    """
    return isinstance(value, dict) and "responses" in value


def _auth_scheme_name() -> str:
    """Return the security scheme name matching the configured auth mode."""
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

        # FastAPI generates most of the schema. This block patches only the
        # security schemes so docs match the runtime auth mode selected by env.
        components = schema.setdefault("components", {})
        security_schemes = components.setdefault("securitySchemes", {})

        security_schemes.update(
            {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            }
        )

        if not settings.AUTH_REQUIRED:
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
            if path_name.startswith(JWT_PATH_PREFIXES):
                security: dict[str, list[Any]] = {"BearerAuth": []}
            elif path_name.startswith(ADMIN_PATH_PREFIXES):
                security = {"AdminToken": []}
            elif path_name.startswith(PUBLIC_PATH_PREFIXES):
                continue
            else:
                security = {_auth_scheme_name(): []}

            for method in path_item.values():
                if _is_operation(method):
                    method.setdefault("security", []).append(security)

        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
