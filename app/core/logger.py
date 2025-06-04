"""Logging configuration for the FastAPI application.

Sets global log level, format, and handlers. Applies consistent settings
to Uvicorn, SQLAlchemy, and Alembic loggers as well.
"""

import logging
import sys

from app.core.settings import settings


def setup_logging() -> None:
    """Initialize application-wide logging configuration."""
    level = logging.getLevelName(settings.LOG_LEVEL)

    fmt = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=datefmt,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        log = logging.getLogger(name)
        log.handlers.clear()
        log.propagate = True
        log.setLevel(level)

    noisy_sql_loggers = (
        "sqlalchemy",
        "sqlalchemy.engine",
        "sqlalchemy.orm",
        "sqlalchemy.pool",
        "alembic",
    )
    for name in noisy_sql_loggers:
        log = logging.getLogger(name)
        log.handlers.clear()
        log.propagate = True

    logging.getLogger("sqlalchemy").setLevel(level)
    logging.getLogger("alembic").setLevel(level)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.ERROR)
