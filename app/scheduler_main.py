"""Standalone entry-point for the delivery-cost scheduler process.

This script launches an APScheduler loop that periodically recalculates
delivery costs. It is intended to run as an independent background worker.
"""

import asyncio
import signal

from app.core.logger import setup_logging
from app.tasks.scheduler import init_scheduler


def main() -> None:
    """Launch the delivery-cost scheduler process.

    Sets up logging, creates a dedicated asyncio event loop, binds
    APScheduler to it, and ensures graceful shutdown on termination signals.
    """
    setup_logging()

    # Create and activate a dedicated asyncio event loop.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Initialize the APScheduler instance bound to this event loop.
    scheduler = init_scheduler(loop)
    scheduler.start()

    # Ensure clean shutdown on SIGINT / SIGTERM.
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, scheduler.shutdown)

    # Enter infinite loop to keep the scheduler alive.
    loop.run_forever()


if __name__ == "__main__":
    main()
