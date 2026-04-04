from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.core.settings import settings


def setup_custom_openapi(app: FastAPI) -> None:
    """Inject custom OpenAPI schema with the appropriate security scheme.

    When AUTH_REQUIRED=True: uses BearerAuth (JWT).
    When AUTH_REQUIRED=False: uses SessionAuth (X-Session-Id header).
    """

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,  # noqa
            version=app.version,  # noqa
            description=app.description,  # noqa
            routes=app.routes,
        )

        if settings.AUTH_REQUIRED:
            schema["components"]["securitySchemes"] = {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            }
            for path in schema.get("paths", {}).values():
                for method in path.values():
                    method.setdefault("security", []).append({"BearerAuth": []})
        else:
            schema["components"]["securitySchemes"] = {
                "SessionAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-Session-Id",
                }
            }
            for path in schema.get("paths", {}).values():
                for method in path.values():
                    method.setdefault("security", []).append({"SessionAuth": []})

        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
