"""Operational routes for manually triggering background tasks.

These endpoints are useful in development and small deployments. If this API is
exposed publicly, protect this router at the gateway or add an auth dependency.
"""

import logging

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import require_task_admin_token
from app.core.rate_limit import limiter
from app.core.settings import settings
from app.redis_client import get_redis
from app.tasks import recalc_delivery_costs

router = APIRouter(prefix="/tasks", tags=["tasks"])

log = logging.getLogger(__name__)


@router.post(
    "/recalc-delivery",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger delivery-cost recalculation manually",
    response_model=dict[str, int],
)
@limiter.limit(settings.RATE_LIMIT_RECALC)
async def manual_recalc(
    request: Request,
    _admin: None = Depends(require_task_admin_token),
) -> dict[str, int]:
    """Manually trigger the delivery cost recalculation task."""
    # This endpoint is an operational escape hatch. The admin-token dependency
    # protects it independently from user/session authentication.
    await get_redis().delete("delivery_job_lock")
    updated = await recalc_delivery_costs()
    log.info("manual_recalc called")
    return {"updated": updated}
