from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", include_in_schema=False)
async def healthcheck():
    """Health check endpoint for infrastructure monitoring.

    Returns:
        dict[str, str]: Always returns ``{"status": "ok"}``.
    """
    return {"status": "ok"}
