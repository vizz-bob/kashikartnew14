from sqlalchemy.orm import Session
from sqlalchemy.future import select
from typing import List, Dict, Optional
import logging
from datetime import datetime
import traceback

from app.models.source import Source, SourceStatus
from app.models.fetch_log import FetchLog, FetchStatus
from app.businessLogic.tender_service import TenderService
from app.scraping.implementations.html_scraper import HTMLScraper
from app.scraping.implementations.pdf_scraper import PDFScraper

logger = logging.getLogger(__name__)


class SourceService:

    @staticmethod
    async def fetch_from_source(db: Session, source_id: int) -> Dict:


        # source = db.query(Source).filter(Source.id == source_id).first()
        result = await db.execute(select(Source).filter(Source.id == source_id))
        source = result.scalars().first()

        if not source:
            logger.error(f"Source {source_id} not found")
            return {"success": False, "message": "Source not found"}

        if not source.is_active:
            logger.warning(f"Source {source.name} is not active")
            return {"success": False, "message": "Source is not active"}

        started_at = datetime.utcnow()

        try:
            logger.info(f"Starting fetch from {source.name}")

            # Update last fetch time
            source.last_fetch_at = started_at
            db.commit()

            # Choose scraper based on type
            if source.scraper_type == "pdf":
                scraper = PDFScraper(source)
            else:
                scraper = HTMLScraper(source)

            # Fetch tenders
            tenders_data = scraper.scrape()

            new_count = 0
            updated_count = 0

            for tender_data in tenders_data:
                # Add source_id
                tender_data['source_id'] = source.id

                # Check if tender exists
                existing = TenderService.check_duplicate(
                    db,
                    tender_data['reference_id'],
                    source.id
                )

                if existing:
                    # Update if content changed
                    TenderService.update_tender(db, existing, tender_data)
                    updated_count += 1
                else:
                    # Create new tender
                    TenderService.create_tender(db, tender_data)
                    new_count += 1

            # Update source stats
            source.total_tenders += new_count
            source.last_success_at = datetime.utcnow()
            source.status = SourceStatus.ACTIVE
            source.consecutive_failures = 0

            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).seconds

            # Create success log
            log = FetchLog(
                source_id=source.id,
                source_name=source.name,
                status=FetchStatus.SUCCESS,
                message=f"Successfully fetched {new_count} new tenders",
                tenders_found=len(tenders_data),
                new_tenders=new_count,
                updated_tenders=updated_count,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration
            )

            db.add(log)
            db.commit()

            logger.info(f"Fetch completed: {source.name} - {new_count} new, {updated_count} updated")

            return {
                "success": True,
                "message": f"Successfully fetched {new_count} new tenders",
                "new_tenders": new_count,
                "updated_tenders": updated_count,
                "total_found": len(tenders_data)
            }

        except Exception as e:
            error_msg = str(e)
            error_details = traceback.format_exc()

            logger.error(f"Error fetching from {source.name}: {error_msg}")
            logger.debug(error_details)

            # Update source status
            source.consecutive_failures += 1

            if source.consecutive_failures >= 3:
                source.status = SourceStatus.ERROR
            else:
                source.status = SourceStatus.WARNING

            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).seconds

            # Create error log
            log = FetchLog(
                source_id=source.id,
                source_name=source.name,
                status=FetchStatus.ERROR,
                message=f"Failed to fetch: {error_msg}",
                error_details=error_details,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration
            )

            db.add(log)
            db.commit()

            return {
                "success": False,
                "message": error_msg,
                "error": error_details
            }

    @staticmethod
    def fetch_from_all_sources(db: Session) -> Dict:


        sources = db.query(Source).filter(Source.is_active == True).all()

        logger.info(f"Starting fetch from {len(sources)} active sources")

        # Create info log
        log = FetchLog(
            source_name="System",
            status=FetchStatus.INFO,
            message="Scheduled sync started",
            started_at=datetime.utcnow()
        )
        db.add(log)
        db.commit()

        results = {
            "total_sources": len(sources),
            "successful": 0,
            "failed": 0,
            "total_new_tenders": 0
        }

        for source in sources:
            result = SourceService.fetch_from_source(db, source.id)

            if result['success']:
                results['successful'] += 1
                results['total_new_tenders'] += result.get('new_tenders', 0)
            else:
                results['failed'] += 1

        logger.info(f"Fetch completed: {results['successful']}/{len(sources)} sources successful")

        return results


# Standalone functions for scheduler
def fetch_from_source(db: Session, source_id: int):
    SourceService.fetch_from_source(db, source_id)


def fetch_from_all_sources(db: Session):
    SourceService.fetch_from_all_sources(db)