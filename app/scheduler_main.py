"""Standalone entry-point for the delivery-cost scheduler process.

This script launches an APScheduler loop that periodically recalculates
delivery costs. It is intended to run as an independent background worker.
"""

import asyncio
import signal

from app.core.logger import setup_logging
from app.core.sentry import init_sentry
from app.redis_client import close_redis
from app.tasks.scheduler import init_scheduler
from app.version import __version__


def main() -> None:
    """Launch the delivery-cost scheduler process.

    Sets up logging, creates a dedicated asyncio event loop, binds
    APScheduler to it, and ensures graceful shutdown on termination signals.
    """
    setup_logging()
    init_sentry(release=__version__)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    scheduler = init_scheduler(loop)
    scheduler.start()

    def _shutdown() -> None:
        # Signal handlers cannot await directly, so schedule async cleanup on
        # the worker loop before stopping it.
        scheduler.shutdown()
        loop.create_task(_cleanup_and_stop())

    async def _cleanup_and_stop() -> None:
        await close_redis()
        loop.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _shutdown)

    loop.run_forever()


if __name__ == "__main__":
    main()
