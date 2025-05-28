from asyncio import AbstractEventLoop

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.tasks.delivery import recalc_delivery_costs


def init_scheduler(loop: AbstractEventLoop) -> AsyncIOScheduler:
    """Initialize and configure the APScheduler with a recurring job.

    Binds the scheduler to the provided asyncio event loop and schedules
    the ``recalc_delivery_costs`` task to run every 5 minutes.

    Args:
        loop: AsyncIO event loop that will drive scheduled job execution.

    Returns:
        AsyncIOScheduler: Configured scheduler instance, not yet started.
    """
    scheduler = AsyncIOScheduler(timezone="UTC", event_loop=loop)
    scheduler.add_job(
        recalc_delivery_costs,
        trigger="cron",  # Run on a recurring schedule.
        minute="*/5",  # Every 5 minutes.
        id="recalc_delivery",  # Unique job ID to allow replacement.
        max_instances=1,  # Prevent overlap if previous run hangs.
        coalesce=True,  # Skip intermediate missed runs.
        replace_existing=True,  # Replace an existing job with the same ID.
    )
    return scheduler
