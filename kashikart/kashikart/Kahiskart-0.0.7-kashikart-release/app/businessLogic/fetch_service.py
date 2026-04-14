from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Dict, List
from app.models.source import Source
from app.models.tender import Tender
from app.models.fetch_log import FetchLog, FetchStatus
from app.scraping.implementations.html_scraper import HTMLScraper
from app.scraping.implementations.pdf_scraper import PDFScraper
from app.scraping.implementations.portal_scraper import PortalScraper
from app.keyword_engine.matcher import KeywordMatcher
from app.businessLogic.notification_service import NotificationService
from app.businessLogic.change_detection_service import ChangeDetectionService
from app.utils.logger import setup_logger

logger = setup_logger()


class FetchService:
    """Service for fetching data from sources"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.keyword_matcher = KeywordMatcher(db)
        self.notification_service = NotificationService(db)
        self.change_detector = ChangeDetectionService(db)

    async def fetch_from_source(self, source_id: int) -> Dict:
        """
        Fetch data from a specific source.

        Args:
            source_id: ID of source to fetch

        Returns:
            Dictionary with fetch results
        """
        # Get source
        source = await self.db.get(Source, source_id)
        if not source:
            raise ValueError(f"Source {source_id} not found")

        if not source.is_active:
            logger.warning(f"Source {source.name} is not active")
            return {"error": "Source is not active"}

        # Create fetch log
        fetch_log = FetchLog(
            source_id=source_id,
            started_at=datetime.utcnow(),
            status=FetchStatus.RUNNING
        )
        self.db.add(fetch_log)
        await self.db.commit()

        try:
            # Get appropriate scraper
            scraper = self._get_scraper(source)

            # Fetch data
            logger.info(f"Starting fetch from {source.name}")
            raw_tenders = await scraper.fetch_data()

            logger.info(f"Fetched {len(raw_tenders)} tenders from {source.name}")

            # Process tenders
            results = await self._process_tenders(raw_tenders, source)

            # Update fetch log
            fetch_log.completed_at = datetime.utcnow()
            fetch_log.duration_seconds = (
                    fetch_log.completed_at - fetch_log.started_at
            ).seconds
            fetch_log.status = FetchStatus.SUCCESS
            fetch_log.tenders_found = results['total']
            fetch_log.tenders_new = results['new']
            fetch_log.tenders_updated = results['updated']

            # Update source
            source.last_fetch_at = datetime.utcnow()
            source.total_tenders_fetched += results['new']
            source.consecutive_failures = 0
            source.is_healthy = True

            await self.db.commit()

            logger.info(
                f"Completed fetch from {source.name}: "
                f"{results['new']} new, {results['updated']} updated"
            )

            return results

        except Exception as e:
            logger.error(f"Error fetching from {source.name}: {e}")

            # Update fetch log
            fetch_log.completed_at = datetime.utcnow()
            fetch_log.status = FetchStatus.FAILED
            fetch_log.error_message = str(e)
            fetch_log.error_type = type(e).__name__

            # Update source
            source.consecutive_failures += 1
            if source.consecutive_failures >= 3:
                source.is_healthy = False

            await self.db.commit()

            return {
                "error": str(e),
                "total": 0,
                "new": 0,
                "updated": 0
            }

    def _get_scraper(self, source: Source):
        """Get appropriate scraper for source type"""
        source_config = {
            'id': source.id,
            'url': source.url,
            'requires_login': source.requires_login,
            'username': source.username,
            'password': source.password_encrypted,  # Will be decrypted
            'max_pages': source.max_pages,
            'parsing_rules': {}  # Parse from JSON if needed
        }

        if source.source_type == 'html':
            return HTMLScraper(source_config)
        elif source.source_type == 'pdf':
            return PDFScraper(source_config)
        elif source.source_type == 'portal':
            return PortalScraper(source_config)
        else:
            return HTMLScraper(source_config)  # Default

    async def _process_tenders(
            self,
            raw_tenders: List[Dict],
            source: Source
    ) -> Dict:
        """
        Process fetched tenders: detect changes, match keywords, send notifications.

        Args:
            raw_tenders: List of tender dictionaries
            source: Source object

        Returns:
            Dictionary with processing results
        """
        results = {
            'total': len(raw_tenders),
            'new': 0,
            'updated': 0,
            'matched': 0
        }

        for tender_data in raw_tenders:
            try:
                # Check if tender exists
                existing = await self._find_existing_tender(tender_data['tender_id'])

                if existing:
                    # Check for changes
                    if self.change_detector.has_changed(existing, tender_data):
                        await self._update_tender(existing, tender_data)
                        results['updated'] += 1
                else:
                    # Create new tender
                    tender = await self._create_tender(tender_data)
                    results['new'] += 1

                    # Match keywords
                    matches = await self.keyword_matcher.match_and_save(tender)

                    if matches > 0:
                        results['matched'] += 1

                        # Send notification
                        await self.notification_service.notify_new_tender(tender)

            except Exception as e:
                logger.error(f"Error processing tender: {e}")
                continue

        return results

    async def _find_existing_tender(self, tender_id: str) -> Tender:
        """Find existing tender by tender_id"""
        query = select(Tender).where(Tender.tender_id == tender_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _create_tender(self, tender_data: Dict) -> Tender:
        """Create new tender"""
        tender = Tender(**tender_data)
        self.db.add(tender)
        await self.db.commit()
        await self.db.refresh(tender)
        return tender

    async def _update_tender(self, tender: Tender, new_data: Dict):
        """Update existing tender"""
        for key, value in new_data.items():
            if hasattr(tender, key) and key not in ['id', 'tender_id', 'created_at']:
                setattr(tender, key, value)

        tender.updated_at = datetime.utcnow()
        tender.version += 1

        await self.db.commit()