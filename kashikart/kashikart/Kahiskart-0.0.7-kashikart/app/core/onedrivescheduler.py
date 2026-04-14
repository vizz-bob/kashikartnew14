from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
from datetime import datetime

from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.businessLogic.excel_processor import ExcelProcessor

logger = logging.getLogger(__name__)

class OneDriveScheduler:
    """Scheduler for automatic OneDrive file processing"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
    
    def start(self):
        """Start the scheduler"""
        if not self.is_running:
            # Schedule OneDrive file check
            self.scheduler.add_job(
                func=self.process_onedrive_file,
                trigger=IntervalTrigger(seconds=settings.ONEDRIVE_POLL_INTERVAL),
                id='onedrive_file_check',
                name='Check and process OneDrive file',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info(f"OneDrive scheduler started. Polling every {settings.ONEDRIVE_POLL_INTERVAL} seconds")
    
    def stop(self):
        """Stop the scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("OneDrive scheduler stopped")
    
    def process_onedrive_file(self):
        """Process OneDrive file - called by scheduler"""
        db = AsyncSessionLocal()
        try:
            logger.info(f"[{datetime.utcnow()}] Checking OneDrive file for updates...")
            
            processor = ExcelProcessor(db)
            file_tracker = processor.process_onedrive_file(
                share_link=settings.ONEDRIVE_SHARE_LINK,
                force_refresh=False  # Only process if file changed
            )
            
            if file_tracker:
                logger.info(f"Successfully processed file: {file_tracker.file_name} "
                          f"({file_tracker.total_rows} rows)")
            else:
                logger.info("No updates to process")
                
        except Exception as e:
            logger.error(f"Error in scheduled OneDrive processing: {str(e)}", exc_info=True)
        finally:
            db.close()
    
    def run_now(self):
        """Manually trigger file processing"""
        logger.info("Manual trigger: Processing OneDrive file now")
        self.process_onedrive_file()

# Global scheduler instance
onedrive_scheduler = OneDriveScheduler()