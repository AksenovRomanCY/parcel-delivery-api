"""Unit tests for APScheduler configuration."""

from unittest.mock import MagicMock

import pytest

from app.core.settings import settings
from app.tasks import scheduler as scheduler_module
from app.tasks.delivery import recalc_delivery_costs
from app.tasks.scheduler import init_scheduler


def test_init_scheduler_registers_delivery_recalculation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scheduler should register the recurring delivery recalculation job."""
    # Arrange
    loop = MagicMock()
    scheduler = MagicMock()
    scheduler_cls = MagicMock(return_value=scheduler)
    monkeypatch.setattr(scheduler_module, "AsyncIOScheduler", scheduler_cls)
    monkeypatch.setattr(settings, "DELIVERY_JOB_INTERVAL_MIN", 7)

    # Act
    result = init_scheduler(loop)

    # Assert
    assert result == scheduler
    scheduler_cls.assert_called_once_with(timezone="UTC", event_loop=loop)
    scheduler.add_job.assert_called_once_with(
        recalc_delivery_costs,
        trigger="cron",
        minute="*/7",
        id="recalc_delivery",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
