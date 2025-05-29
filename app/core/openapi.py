from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def setup_custom_openapi(app: FastAPI) -> None:
    """Inject custom OpenAPI schema with SessionAuth support.

    This function modifies the default OpenAPI schema to include a
    reusable security scheme (based on `X-Session-Id`) and applies it
    globally to all endpoints.

    Args:
        app: The FastAPI application instance to patch.
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

        # Define reusable security scheme
        schema["components"]["securitySchemes"] = {
            "SessionAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Session-Id",
            }
        }

        # Apply scheme to all operations
        for path in schema.get("paths", {}).values():
            for method in path.values():
                method.setdefault("security", []).append({"SessionAuth": []})

        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi
