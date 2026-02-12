import logging
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.scraper import run_scraper
from src.settings import config

log = logging.getLogger("scheduler")


def setup_scheduler():
    scheduler = AsyncIOScheduler(timezone=ZoneInfo(config.TIMEZONE))

    scheduler.add_job(run_scraper, "cron", hour=12, minute=0, args=[config.START_URL])

    scheduler.start()
    for job in scheduler.get_jobs():
        log.info("Job %s next_run_time=%s", job.id, job.next_run_time)
