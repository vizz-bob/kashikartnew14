from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.scheduler.jobs import fetch_all_sources_job
from app.core.config import settings

# settings = settings() # settings is already an instance
scheduler = BackgroundScheduler(timezone=settings.SCHEDULER_TIMEZONE)


def start_scheduler():
    """Initialize and start the scheduler"""

    # Daily fetch at configured time
    hour, minute = settings.DEFAULT_FETCH_TIME.split(':')
    scheduler.add_job(
        fetch_all_sources_job,
        CronTrigger(hour=int(hour), minute=int(minute)),
        id='daily_fetch',
        replace_existing=True
    )

    scheduler.start()
    print(" Scheduler started")


def stop_scheduler():
    """Stop the scheduler"""
    scheduler.shutdown()