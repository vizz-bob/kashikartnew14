# from apscheduler.schedulers.background import BackgroundScheduler
# from apscheduler.triggers.cron import CronTrigger
# from app.core.config import settings
# import logging
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.core.database import AsyncSessionLocal

# logger = logging.getLogger(__name__)

# scheduler = BackgroundScheduler(timezone=settings.SCHEDULER_TIMEZONE)


# async def fetch_all_sources_job():
#     from app.businessLogic.source_service import fetch_from_all_sources

#     async with AsyncSessionLocal() as db:
#         try:
#             logger.info("Starting scheduled fetch job...")
#             await fetch_from_all_sources(db)
#             logger.info("Scheduled fetch job completed")
#         except Exception as e:
#             logger.error(f"Error in scheduled fetch job: {str(e)}")


# async def keyword_matching_job():
#     from app.businessLogic.tender_service import run_keyword_matching

#     async with AsyncSessionLocal() as db:
#         try:
#             logger.info("Starting keyword matching job...")
#             await run_keyword_matching(db)
#             logger.info("Keyword matching job completed")
#         except Exception as e:
#             logger.error(f"Error in keyword matching job: {str(e)}")


# # Add jobs to scheduler
# scheduler.add_job(
#     fetch_all_sources_job,
#     CronTrigger(hour='*/6'),  # Every 6 hours
#     id='fetch_all_sources',
#     name='Fetch all tender sources',
#     replace_existing=True
# )

# scheduler.add_job(
#     keyword_matching_job,
#     CronTrigger(hour='*/1'),  # Every hour
#     id='keyword_matching',
#     name='Run keyword matching',
#     replace_existing=True
# )

# import asyncio
# import logging
# from apscheduler.schedulers.background import BackgroundScheduler
# from apscheduler.triggers.cron import CronTrigger
# from app.core.config import settings
# from app.core.database import AsyncSessionLocal
# from app.businessLogic.excel_processor_local import ExcelProcessorLocal

# logger = logging.getLogger(__name__)

# # Background Scheduler (Windows EXE Safe)
# scheduler = BackgroundScheduler(timezone=settings.SCHEDULER_TIMEZONE)

# # ==============================
# # CREATE GLOBAL EVENT LOOP FOR SCHEDULER THREAD
# # ==============================
# scheduler_loop = asyncio.new_event_loop()

# # JOB LOCK FLAG (ADD HERE)
# JOB_RUNNING = False

# # ==============================
# # ASYNC JOB WRAPPER (FIXED)
# # ==============================
# def run_async(coro_func):
#     try:
#         scheduler_loop.run_until_complete(coro_func())
#     except Exception as e:
#         logger.error(f"Scheduler Async Error: {e}")


# # ==============================
# # EXCEL AUTO FETCH JOB
# # ==============================
# # async def excel_auto_fetch_job():
# #     logger.info("AUTO Excel fetch started")
# #     await ExcelProcessorLocal.process_all_registered_files()
# #     logger.info("AUTO Excel fetch finished")
# async def excel_auto_fetch_job():
#     global JOB_RUNNING

#     if JOB_RUNNING:
#         logger.warning("Excel job already running, skipping...")
#         return

#     JOB_RUNNING = True
#     try:
#         logger.info("AUTO Excel fetch started")
#         await ExcelProcessorLocal.process_all_registered_files()
#         logger.info("AUTO Excel fetch finished")
#     except Exception as e:
#         logger.error(f"Excel auto fetch error: {e}")
#     finally:
#         JOB_RUNNING = False



# # ==============================
# # EXISTING JOBS (UNCHANGED)
# # ==============================
# async def fetch_all_sources_job():
#     from app.businessLogic.source_service import fetch_from_all_sources

#     async with AsyncSessionLocal() as db:
#         try:
#             logger.info("Starting scheduled fetch job...")
#             await fetch_from_all_sources(db)
#             logger.info("Scheduled fetch job completed")
#         except Exception as e:
#             logger.error(f"Error in scheduled fetch job: {str(e)}")


# async def keyword_matching_job():
#     from app.businessLogic.tender_service import run_keyword_matching

#     async with AsyncSessionLocal() as db:
#         try:
#             logger.info("Starting keyword matching job...")
#             await run_keyword_matching(db)
#             logger.info("Keyword matching job completed")
#         except Exception as e:
#             logger.error(f"Error in keyword matching job: {str(e)}")


# # ==============================
# # REGISTER JOBS (IMPORTANT FIX)
# # ==============================

# scheduler.add_job(
#     run_async,
#     args=[excel_auto_fetch_job],  # ✅ DO NOT CALL
#     trigger="interval",
#     minutes=1,
#     id="excel_auto_fetch",
#     replace_existing=True
# )

# scheduler.add_job(
#     run_async,
#     args=[fetch_all_sources_job],  # ❌ removed ()
#     trigger=CronTrigger(hour="*/6"),
#     id="fetch_all_sources",
#     replace_existing=True
# )

# scheduler.add_job(
#     run_async,
#     args=[keyword_matching_job],  # ❌ removed ()
#     trigger=CronTrigger(hour="*/1"),
#     id="keyword_matching",
#     replace_existing=True
# )


# # ==============================
# # START SCHEDULER
# # ==============================
# def start_scheduler():
#     try:
#         # Attach loop to scheduler thread
#         asyncio.set_event_loop(scheduler_loop)

#         scheduler.start()
#         logger.info("Background Scheduler Started")
#     except Exception as e:
#         logger.error(f"Scheduler start error: {str(e)}")

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.config import settings
from app.businessLogic.excel_processor_sync import ExcelProcessorSync

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone=settings.SCHEDULER_TIMEZONE)

# Prevent double execution
JOB_RUNNING = False

def excel_job():
    global JOB_RUNNING
    if JOB_RUNNING:
        logger.warning("Excel job already running")
        return

    JOB_RUNNING = True
    try:
        logger.info("Excel Auto Fetch Started")
        ExcelProcessorSync.process_all_registered_files()
        logger.info("Excel Auto Fetch Finished")
    except Exception as e:
        logger.error(f"Excel Scheduler Error: {e}")
    finally:
        JOB_RUNNING = False


# Register jobs
scheduler.add_job(
    excel_job,
    IntervalTrigger(minutes=1),
    id="excel_auto_fetch",
    replace_existing=True
)

# Auto tender sync every 20 mins
def tender_sync_job():
    from app.businessLogic.source_service import fetch_from_all_sources
    from app.businessLogic.notification_service import NotificationService
    try:
        result = fetch_from_all_sources()
        logger.info(f"Auto sync result: {result}")
        NotificationService().send_system_notification(
            title="Auto Sync Complete",
            message=f"Synced {result.get('total_new_tenders', 0)} new tenders from {result.get('successful', 0)} sources"
        )
    except Exception as e:
        logger.error(f"Auto tender sync error: {e}")

scheduler.add_job(
    tender_sync_job,
    IntervalTrigger(minutes=20),
    id="auto_tender_sync",
    replace_existing=True
)


def start_scheduler():
    scheduler.start()
    logger.info("Background Scheduler Started")
