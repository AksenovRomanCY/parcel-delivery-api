from decimal import Decimal
from typing import Sequence

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.parcel import Parcel
from app.redis_client import get_redis
from app.services.rates import get_usd_rub_rate

log = structlog.get_logger(__name__)


async def _acquire_lock(ttl: int = 330) -> bool:
    """Attempt to acquire a Redis NX-lock for job deduplication.

    Prevents concurrent delivery-cost recalculations from running at
    the same time (e.g., in parallel containers or deployments).

    Args:
        ttl: Lock expiration time in seconds (default 330 sec.).

    Returns:
        bool: True if the lock was acquired successfully, False otherwise.
    """
    redis = get_redis()
    return await redis.set("delivery_job_lock", "1", ex=ttl, nx=True)


async def _fetch_unpriced(session: AsyncSession, batch: int = 500) -> Sequence[Parcel]:
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


async def _formula(weight: float, declared: Decimal, rate: Decimal) -> Decimal:
    """Calculate delivery cost based on weight, value, and currency rate.

    Args:
        weight: Parcel weight in kilograms.
        declared: Declared USD value of the parcel.
        rate: USD to RUB conversion rate.

    Returns:
        Decimal: Final delivery cost in rubles.
    """
    return (Decimal(weight) * Decimal("0.5") + declared * Decimal("0.01")) * rate


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
        log.info("delivery_job_skip", reason="lock_exists")
        return 0

    rate = await get_usd_rub_rate()
    updated = 0

    async with AsyncSessionLocal() as session:
        while parcels := await _fetch_unpriced(session):
            for parcel in parcels:
                parcel.delivery_cost_rub = float(
                    await _formula(
                        parcel.weight_kg,
                        Decimal(parcel.declared_value_usd),
                        rate,
                    )
                )
            await session.commit()
            updated += len(parcels)

    await get_redis().set("delivery_last_run_ts", str(updated))
    log.info("delivery_job_done", updated=updated, rate=float(rate))
    return updated
