import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="America/New_York")
    return _scheduler


def start_scheduler(daily_nudge_fn, followup_check_fn):
    scheduler = get_scheduler()

    scheduler.add_job(
        daily_nudge_fn,
        CronTrigger(hour=7, minute=0),
        id="daily_nudge",
        replace_existing=True,
        name="Daily 7AM accountability nudge",
    )

    scheduler.add_job(
        followup_check_fn,
        IntervalTrigger(hours=2, start_date="2024-01-01 08:00:00"),
        id="followup_check",
        replace_existing=True,
        name="Follow-up check every 2hrs",
    )

    scheduler.start()
    logger.info("Scheduler started: daily nudge at 7AM, follow-up checks every 2hrs")


def stop_scheduler():
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown()
