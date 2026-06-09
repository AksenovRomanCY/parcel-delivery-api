"""Unit tests for the standalone scheduler entrypoint."""

import asyncio
import signal
from collections.abc import Callable, Coroutine
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app import scheduler_main
from app.version import __version__


@pytest.mark.asyncio
async def test_main_wires_scheduler_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scheduler main should wire logging, signals, scheduler, and cleanup."""
    # Arrange
    loop = MagicMock()
    scheduler = MagicMock()
    signal_handlers: dict[int, Callable[[], None]] = {}
    created_tasks: list[Coroutine[Any, Any, None]] = []

    def _add_signal_handler(sig: signal.Signals, callback: Callable[[], None]) -> None:
        signal_handlers[int(sig)] = callback

    def _create_task(coro: Coroutine[Any, Any, None]) -> MagicMock:
        created_tasks.append(coro)
        return MagicMock()

    loop.add_signal_handler.side_effect = _add_signal_handler
    loop.create_task.side_effect = _create_task

    setup_logging = MagicMock()
    init_sentry = MagicMock()
    init_scheduler = MagicMock(return_value=scheduler)
    close_redis = AsyncMock()
    monkeypatch.setattr(scheduler_main, "setup_logging", setup_logging)
    monkeypatch.setattr(scheduler_main, "init_sentry", init_sentry)
    monkeypatch.setattr(scheduler_main, "init_scheduler", init_scheduler)
    monkeypatch.setattr(scheduler_main, "close_redis", close_redis)
    monkeypatch.setattr(asyncio, "new_event_loop", lambda: loop)
    set_event_loop = MagicMock()
    monkeypatch.setattr(asyncio, "set_event_loop", set_event_loop)

    # Act
    scheduler_main.main()
    signal_handlers[int(signal.SIGTERM)]()
    await created_tasks[0]

    # Assert
    setup_logging.assert_called_once_with()
    init_sentry.assert_called_once_with(release=__version__)
    set_event_loop.assert_called_once_with(loop)
    init_scheduler.assert_called_once_with(loop)
    scheduler.start.assert_called_once_with()
    assert set(signal_handlers) == {int(signal.SIGINT), int(signal.SIGTERM)}
    loop.run_forever.assert_called_once_with()
    scheduler.shutdown.assert_called_once_with()
    close_redis.assert_awaited_once_with()
    loop.stop.assert_called_once_with()
