import logging
import sys

from app.core.settings import settings


def setup_logging() -> None:
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

    # Настроим Uvicorn/SQLAlchemy логгеры
    for logger_name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "sqlalchemy",
        "alembic",
    ):
        logging.getLogger(logger_name).setLevel(level)
        logging.getLogger(logger_name).propagate = True
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
