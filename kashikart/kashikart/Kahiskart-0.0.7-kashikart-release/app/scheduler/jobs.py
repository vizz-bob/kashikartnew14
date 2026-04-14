from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from typing import List
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.source import Source
from app.models.fetch_log import FetchLog, FetchStatus
from app.businessLogic.fetch_service import FetchService
from app.utils.logger import setup_logger

logger = setup_logger()

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def fetch_all_sources_job():
    """
    Scheduled job to fetch data from all active sources.
    This runs on the configured schedule (daily, hourly, etc.)
    """
    logger.info("Starting scheduled fetch for all sources")

    async with AsyncSessionLocal() as db:
        try:
            # Get all active sources
            query = select(Source).where(Source.is_active == True)
            result = await db.execute(query)
            sources = result.scalars().all()

            logger.info(f"Found {len(sources)} active sources to fetch")

            fetch_service = FetchService(db)

            # Fetch from each source
            for source in sources:
                try:
                    logger.info(f"Fetching from source: {source.name}")
                    await fetch_service.fetch_from_source(source.id)

                except Exception as e:
                    logger.error(f"Error fetching from source {source.name}: {e}")
                    continue

            logger.info("Completed scheduled fetch for all sources")

        except Exception as e:
            logger.error(f"Error in fetch_all_sources_job: {e}")


async def fetch_single_source_job(source_id: int):
    """
    Job to fetch data from a single source.

    Args:
        source_id: ID of source to fetch
    """
    logger.info(f"Starting fetch for source ID: {source_id}")

    async with AsyncSessionLocal() as db:
        try:
            fetch_service = FetchService(db)
            result = await fetch_service.fetch_from_source(source_id)

            logger.info(
                f"Completed fetch for source {source_id}. "
                f"Found {result.get('tenders_new', 0)} new tenders"
            )

        except Exception as e:
            logger.error(f"Error in fetch_single_source_job for source {source_id}: {e}")


async def send_digest_job(period: str = "daily"):
    """
    Job to send digest emails.

    Args:
        period: 'daily' or 'weekly'
    """
    logger.info(f"Starting {period} digest job")

    async with AsyncSessionLocal() as db:
        try:
            from app.businessLogic.notification_service import NotificationService

            notification_service = NotificationService(db)
            await notification_service.send_digest_notifications(period)

            logger.info(f"Completed {period} digest job")

        except Exception as e:
            logger.error(f"Error in send_digest_job: {e}")


async def cleanup_old_data_job():
    """
    Job to cleanup old data (logs, expired tenders, etc.)
    Runs weekly.
    """
    logger.info("Starting data cleanup job")

    async with AsyncSessionLocal() as db:
        try:
            # Delete old fetch logs (older than 90 days)
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=90)

            query = select(FetchLog).where(FetchLog.started_at < cutoff_date)
            result = await db.execute(query)
            old_logs = result.scalars().all()

            for log in old_logs:
                await db.delete(log)

            await db.commit()

            logger.info(f"Deleted {len(old_logs)} old fetch logs")

        except Exception as e:
            logger.error(f"Error in cleanup_old_data_job: {e}")


def setup_scheduler():
    """
    Setup and configure the scheduler with all jobs.
    Called on application startup.
    """
    logger.info("Setting up scheduler...")

    # Main fetch job - runs daily at configured time (default 9:00 AM)
    scheduler.add_job(
        fetch_all_sources_job,
        trigger=CronTrigger(hour=9, minute=0),
        id='fetch_all_sources',
        name='Fetch all sources daily',
        replace_existing=True
    )

    # Hourly quick check for high-priority sources
    scheduler.add_job(
        fetch_all_sources_job,
        trigger=IntervalTrigger(hours=1),
        id='fetch_hourly',
        name='Hourly fetch check',
        replace_existing=True
    )

    # Daily digest - 6:00 PM
    scheduler.add_job(
        send_digest_job,
        trigger=CronTrigger(hour=18, minute=0),
        kwargs={'period': 'daily'},
        id='daily_digest',
        name='Send daily digest',
        replace_existing=True
    )

    # Weekly digest - Monday 9:00 AM
    scheduler.add_job(
        send_digest_job,
        trigger=CronTrigger(day_of_week='mon', hour=9, minute=0),
        kwargs={'period': 'weekly'},
        id='weekly_digest',
        name='Send weekly digest',
        replace_existing=True
    )

    # Weekly cleanup - Sunday 2:00 AM
    scheduler.add_job(
        cleanup_old_data_job,
        trigger=CronTrigger(day_of_week='sun', hour=2, minute=0),
        id='weekly_cleanup',
        name='Weekly data cleanup',
        replace_existing=True
    )

    logger.info("Scheduler configured with jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name} ({job.id})")


def start_scheduler():
    """Start the scheduler"""
    logger.info("Starting scheduler...")
    scheduler.start()
    logger.info("Scheduler started successfully")


def stop_scheduler():
    """Stop the scheduler"""
    logger.info("Stopping scheduler...")
    scheduler.shutdown()
    logger.info("Scheduler stopped")


async def trigger_immediate_fetch(source_id: int = None):
    """
    Trigger an immediate fetch (manual refresh).

    Args:
        source_id: Optional specific source ID. If None, fetches all sources.
    """
    if source_id:
        logger.info(f"Triggering immediate fetch for source {source_id}")
        await fetch_single_source_job(source_id)
    else:
        logger.info("Triggering immediate fetch for all sources")
        await fetch_all_sources_job()