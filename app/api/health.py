"""Health-check endpoint used by orchestration and uptime probes.

The endpoint is intentionally tiny and excluded from OpenAPI. It verifies that
the ASGI app is alive, not that database or Redis dependencies are healthy.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", include_in_schema=False)
async def healthcheck() -> dict[str, str]:
    """Health check endpoint for infrastructure monitoring.

    Returns:
        dict[str, str]: Always returns ``{"status": "ok"}``.
    """
    return {"status": "ok"}
