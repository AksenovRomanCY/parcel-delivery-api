"""Sentry SDK initialization helper.

Called from both app/main.py (FastAPI) and app/scheduler_main.py (worker).
"""

import sentry_sdk

from app.core.settings import settings


def init_sentry(release: str = "0.1.0") -> None:
    """Initialize Sentry if a DSN is configured."""
    if not settings.SENTRY_DSN:
        return
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        environment=settings.ENVIRONMENT,
        release=release,
    )
