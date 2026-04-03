"""Getting and caching USD→RUB rate."""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Final

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.settings import settings
from app.redis_client import get_redis

log = logging.getLogger(__name__)

CBR_URL: Final[str] = "https://www.cbr-xml-daily.ru/daily_json.js"
KEY_TMPL: Final[str] = "usd_rub:{date}"


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
async def _fetch_rate_from_cbr() -> Decimal:
    """Go to an external service (up to 3 attempts) and return the Decimal rate."""
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(CBR_URL)
        resp.raise_for_status()
        data = resp.json()
    return Decimal(str(data["Valute"]["USD"]["Value"]))


async def get_usd_rub_rate() -> Decimal:
    redis = get_redis()
    today = datetime.now(UTC).date().isoformat()
    key = KEY_TMPL.format(date=today)

    if (cached := await redis.get(key)) is not None:
        raw = cached.decode() if isinstance(cached, (bytes, bytearray)) else cached
        return Decimal(raw)

    rate = await _fetch_rate_from_cbr()
    await redis.set(key, str(rate), ex=settings.CACHE_TTL_RATE)
    log.info("usd_rub_rate_fetched: rate=%r", float(rate))
    return rate
