import logging
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.db.session import AsyncSessionLocal
from app.models.parcel import Parcel
from app.redis_client import get_redis
from app.services.rates import get_usd_rub_rate

log = logging.getLogger(__name__)


async def _acquire_lock(ttl: int = settings.DELIVERY_LOCK_TTL) -> bool:
    """Attempt to acquire a Redis NX-lock for job deduplication.

    Prevents concurrent delivery-cost recalculations from running at
    the same time (e.g., in parallel containers or deployments).

    Args:
        ttl: Lock expiration time in seconds (default 330 sec.).

    Returns:
        bool: True if the lock was acquired successfully, False otherwise.
    """
    redis = get_redis()
    return bool(await redis.set("delivery_job_lock", "1", ex=ttl, nx=True))


async def _fetch_unpriced(
    session: AsyncSession, batch: int = settings.DELIVERY_BATCH_SIZE
) -> Sequence[Parcel]:
    """Fetch a batch of parcels that do not yet have delivery costs.

    Args:
        session: Active SQLAlchemy session.
        batch: Max number of rows to retrieve in a single fetch.

    Returns:
        Sequence[Parcel]: Parcels with ``delivery_cost_rub IS NULL``.
    """
    stmt = select(Parcel).where(Parcel.delivery_cost_rub.is_(None)).limit(batch)
    res = await session.scalars(stmt)
    return res.all()


async def _formula(weight: Decimal, declared: Decimal, rate: Decimal) -> Decimal:
    """Calculate delivery cost based on weight, value, and currency rate.

    Args:
        weight: Parcel weight in kilograms.
        declared: Declared USD value of the parcel.
        rate: USD to RUB conversion rate.

    Returns:
        Decimal: Final delivery cost in rubles.
    """
    cost = weight * settings.DELIVERY_WEIGHT_COEFF
    cost += declared * settings.DELIVERY_VALUE_COEFF
    return cost * rate


async def recalc_delivery_costs() -> int:
    """Recalculate delivery costs for all unprocessed parcels.

    This function:
    - Acquires a Redis lock to avoid race conditions;
    - Fetches parcels in batches where ``delivery_cost_rub`` is null;
    - Applies a pricing formula using the current USD/RUB rate;
    - Commits updates to the database;
    - Logs completion and stores metadata in Redis.

    Returns:
        int: Number of parcels successfully updated.
    """
    if not await _acquire_lock():
        log.info("delivery_job_skip: reason=lock_exists")
        return 0

    rate = await get_usd_rub_rate()
    updated = 0

    async with AsyncSessionLocal() as session:
        while parcels := await _fetch_unpriced(session):
            for parcel in parcels:
                parcel.delivery_cost_rub = await _formula(
                    parcel.weight_kg,
                    parcel.declared_value_usd,
                    rate,
                )
            await session.commit()
            updated += len(parcels)

    await get_redis().set("delivery_last_run_ts", str(updated))
    log.info("delivery_job_done: updated=%u, rate=%r", updated, float(rate))
    return updated
