from sqlalchemy.orm import Session
from app.models.source import Source
from app.scraping.implementations import (
    HTMLScraper,
    PDFScraper,
    PortalScraper,
    WebScraperIOScraper
)
from app.models.fetch_log import FetchLog, FetchStatus
from datetime import datetime

SCRAPER_MAP = {
    "html": HTMLScraper,
    "pdf": PDFScraper,
    "portal": PortalScraper,
    "webscraper_io": WebScraperIOScraper,
}

async def run_all_sources(db: Session):
    sources = (
        db.query(Source)
        .filter(Source.is_active == True)
        .filter(Source.status == "ACTIVE")
        .all()
    )

    for source in sources:
        scraper_class = SCRAPER_MAP.get(source.scraper_type)

        if not scraper_class:
            continue

        scraper = scraper_class(source)

        try:
            # Note: In a real async environment, this would be await scraper.scrape()
            # This runner seems to be a template or for a sync worker.
            tenders = await scraper.scrape() 

            source.total_tenders += len(tenders)
            source.last_success_at = datetime.utcnow()

            db.add(FetchLog(
                source_id=source.id,
                source_name=source.name,
                status=FetchStatus.SUCCESS,
                message="Scraping successful",
                tenders_found=len(tenders)
            ))

        except Exception as e:
            db.add(FetchLog(
                source_id=source.id,
                source_name=source.name,
                status=FetchStatus.ERROR,
                message="Scraping failed",
                error_details=str(e)
            ))

        db.commit()
