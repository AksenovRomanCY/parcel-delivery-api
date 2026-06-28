"""Operational routes for manually triggering background tasks.

These endpoints are useful in development and small deployments. If this API is
exposed publicly, protect this router at the gateway or add an auth dependency.
"""

import logging

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import require_task_admin_token
from app.api.examples import FORBIDDEN_ERROR_EXAMPLE, TASK_RECALC_RESPONSE_EXAMPLE
from app.core.rate_limit import limiter
from app.core.settings import settings
from app.redis_client import get_redis
from app.schemas import ErrorResponse
from app.tasks.delivery import recalc_delivery_costs

router = APIRouter(prefix="/tasks", tags=["tasks"])

log = logging.getLogger(__name__)


@router.post(
    "/recalc-delivery",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger delivery-cost recalculation manually",
    response_model=dict[str, int],
    responses={
        202: {
            "description": "Delivery-cost recalculation completed.",
            "content": {"application/json": {"example": TASK_RECALC_RESPONSE_EXAMPLE}},
        },
        403: {
            "model": ErrorResponse,
            "description": "Manual trigger is disabled or admin token is invalid.",
            "content": {"application/json": {"example": FORBIDDEN_ERROR_EXAMPLE}},
        },
    },
)
@limiter.limit(settings.RATE_LIMIT_RECALC)
async def manual_recalc(
    request: Request,
    _admin: None = Depends(require_task_admin_token),
) -> dict[str, int]:
    """Manually trigger the delivery cost recalculation task.

    Intended for operators and local development. The admin-token dependency is
    independent from user auth because this action affects all parcels.
    """
    # This endpoint is an operational escape hatch. The admin-token dependency
    # protects it independently from user/session authentication.
    # Clear a stale lock before running manually; the task will acquire a fresh
    # lock immediately and still deduplicate concurrent invocations.
    await get_redis().delete("delivery_job_lock")
    updated = await recalc_delivery_costs()
    log.info("manual_recalc called")
    return {"updated": updated}
