"""Debug routes for manually triggering background tasks.

Intended for development or admin access to task logic without relying
on the scheduler.
"""

import logging

from fastapi import APIRouter, status

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
async def manual_recalc() -> dict[str, int]:
    """Manually trigger the delivery cost recalculation task.

    Runs the same logic used by the scheduled background job, updating
    delivery costs for all eligible parcels.

    Returns:
        dict[str, int]: A dictionary with the number of updated parcels,
        e.g. ``{"updated": 42}``.
    """
    await get_redis().delete("delivery_job_lock")
    updated = await recalc_delivery_costs()
    log.info("manual_recalc called")
    return {"updated": updated}
