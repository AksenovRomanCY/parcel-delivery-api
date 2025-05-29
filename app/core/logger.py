"""Logging configuration for the FastAPI application.

Sets global log level, format, and handlers. Applies consistent settings
to Uvicorn, SQLAlchemy, and Alembic loggers as well.
"""

import logging
import sys

from app.core.settings import settings


def setup_logging() -> None:
    """Initialize application-wide logging configuration.

    Applies a unified format to stdout logging and configures logging
    levels for internal and third-party modules like Uvicorn and SQLAlchemy.

    Reads log level from ``settings.LOG_LEVEL`` (e.g., "INFO", "DEBUG").
    """
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

    # Configure known loggers for consistency and visibility.
    for logger_name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "sqlalchemy",
        "alembic",
    ):
        logging.getLogger(logger_name).setLevel(level)
        logging.getLogger(logger_name).propagate = True

    # Fine-tune verbosity for specific SQLAlchemy submodules.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
