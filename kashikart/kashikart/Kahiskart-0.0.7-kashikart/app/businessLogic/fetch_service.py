from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Dict, List, Optional
from app.models.source import Source
from app.models.keyword import Keyword
from app.models.tender import Tender
from app.models.fetch_log import FetchLog, FetchStatus
from app.scraping.implementations.html_scraper import HTMLScraper
from app.scraping.implementations.pdf_scraper import PDFScraper
from app.scraping.implementations.portal_scraper import PortalScraper
from app.scraping.implementations.web_scraper_io import WebScraperIOScraper
from app.scraping.implementations.api_scraper import APIBasedScraper
from app.keyword_engine.matcher import KeywordMatcher
from app.businessLogic.notification_service import NotificationService
from app.businessLogic.change_detection_service import ChangeDetectionService
from app.utils.logger import setup_logger

import os
logger = setup_logger(__name__, log_file=os.path.join("logs", "fetch_service.log"))


class FetchService:
    """Service for fetching data from sources"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.keyword_matcher = KeywordMatcher(db)
        self.notification_service = NotificationService(db)
        self.change_detector = ChangeDetectionService(db)

    async def fetch_from_source(self, source_id: int, keywords: Optional[List[str]] = None) -> Dict:
        """
        Fetch data from a specific source.

        Args:
            source_id: ID of source to fetch
            keywords: Optional list of keywords to use for pre-filtering.
                      If None, all active keywords in the DB are used.

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
            source_name=source.name,
            started_at=datetime.utcnow(),
            status=FetchStatus.RUNNING,
            message="Starting fetch..."
        )
        self.db.add(fetch_log)
        await self.db.commit()

        try:
            # Get appropriate scraper
            scraper = self._get_scraper(source)

            # Fetch data
            logger.info(f"Starting fetch from {source.name}")
            raw_tenders = await scraper.scrape()
            print(f"DEBUG: raw_tenders len={len(raw_tenders)}")

            # Pre-filter raw tenders by keywords (title+description) to reduce noise
            raw_tenders = await self._filter_by_keywords(raw_tenders, keywords)
            logger.info(f"Filtered to {len(raw_tenders)} tenders after keyword pre-check")

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
            fetch_log.new_tenders = results['new']
            fetch_log.updated_tenders = results['updated']
            fetch_log.message = f"Fetched {results['total']} tenders: {results['new']} new, {results['updated']} updated"

            # Update source
            source.last_fetch_at = datetime.utcnow()
            source.total_tenders += results['new']
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
            fetch_log.message = f"Fetch failed: {str(e)[:100]}"
            fetch_log.error_details = f"Full error: {str(e)}\nTraceback might be needed."

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

        if source.scraper_type == 'html':
            return HTMLScraper(source)
        elif source.scraper_type == 'pdf':
            return PDFScraper(source)
        elif source.scraper_type == 'portal':
            return PortalScraper(source)
        elif source.scraper_type == 'webscraper_io':
            return WebScraperIOScraper(source)
        elif source.scraper_type == 'api':
            return APIBasedScraper(source)
        else:
            return HTMLScraper(source)  # Default

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
                # Ensure source_id is present
                tender_data['source_id'] = source.id
                
                # Check if tender exists
                ref_id = tender_data.get('reference_id')
                print(f"DEBUG: Processing tender ref_id={ref_id}")
                existing = await self._find_existing_tender(ref_id)

                if existing:
                    # Check for changes
                    if self.change_detector.has_changed(existing, tender_data):
                        await self._update_tender(existing, tender_data)
                        results['updated'] += 1
                else:
                    # Create new tender
                    print(f"DEBUG: Creating new tender for {ref_id}")
                    tender = await self._create_tender(tender_data)
                    results['new'] += 1

                    # Match keywords
                    matches = await self.keyword_matcher.match_and_save(tender)

                    if matches > 0:
                        results['matched'] += 1

                    # Notify system/users for every new tender (regardless of keyword match)
                    await self.notification_service.notify_new_tender(tender)

            except Exception as e:
                logger.error(f"Error processing tender: {e}")
                continue

        return results

    async def _filter_by_keywords(
        self,
        tenders: List[Dict],
        keywords: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Lightweight pre-filter: keep tenders whose title/description contain any
        provided keyword (case-insensitive). If no keywords are provided, falls
        back to all active keywords in the DB. If still empty, returns original
        list.
        """
        # Allow caller to pass an explicit keyword set; otherwise load active ones
        keyword_list: List[str] = [
            k.strip().lower() for k in (keywords or []) if k and k.strip()
        ]

        if not keyword_list:
            result = await self.db.execute(
                select(Keyword.keyword).where(Keyword.is_active == True)
            )
            keyword_list = [k.lower() for k in result.scalars().all()]

        if not keyword_list:
            return tenders

        keyword_set = set(keyword_list)
        filtered = []
        for t in tenders:
            text = f"{t.get('title','')} {t.get('description','')}".lower()
            if any(k in text for k in keyword_set):
                filtered.append(t)

        return filtered

    async def _find_existing_tender(self, reference_id: str) -> Tender:
        """Find existing tender by reference_id"""
        # The provided code edit for this method was syntactically incorrect and
        # seemed to mix logic from a scraper into the FetchService.
        # Assuming the intent was to ensure the reference_id is properly handled
        # before querying, and given the original line was correct,
        # I'm keeping the original query logic.
        # If the intent was to modify how reference_id is derived or validated
        # within the FetchService, please provide a syntactically correct and
        # contextually appropriate code snippet.
        query = select(Tender).where(Tender.reference_id == reference_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _create_tender(self, tender_data: Dict) -> Tender:
        """Create new tender"""
        # Generate content hash
        tender_data['content_hash'] = self.change_detector.generate_hash(tender_data)
        
        tender = Tender(**tender_data)
        self.db.add(tender)
        await self.db.flush() # Ensure ID is generated
        return tender

    async def _update_tender(self, tender: Tender, new_data: Dict):
        """Update existing tender"""
        # Update content hash
        new_data['content_hash'] = self.change_detector.generate_hash(new_data)
        
        for key, value in new_data.items():
            if hasattr(tender, key) and key not in ['id', 'tender_id', 'created_at']:
                setattr(tender, key, value)

        tender.updated_at = datetime.utcnow()
        tender.version += 1
        await self.db.flush()
