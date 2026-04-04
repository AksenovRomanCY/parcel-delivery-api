"""Debug routes for manually triggering background tasks."""

import logging

from fastapi import APIRouter, Request, status

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
async def manual_recalc(request: Request) -> dict[str, int]:
    """Manually trigger the delivery cost recalculation task."""
    await get_redis().delete("delivery_job_lock")
    updated = await recalc_delivery_costs()
    log.info("manual_recalc called")
    return {"updated": updated}
