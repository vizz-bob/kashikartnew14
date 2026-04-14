from typing import List, Dict
from app.models.source import Source

class ScraperService:
    
    async def scrape_tenders_from_source(source: Source) -> List[Dict]:
        """
        Dummy scraper (Step 1 learning version)
        Later you will replace this with Playwright / Selenium / PDF parsing.
        """

        # FOR NOW: return sample test data so your system works
        return [
            {
                "reference_id": "REF-001",
                "title": "IT Software Development Tender",
                "description": "Government tender for IT services",
                "deadline_date": "2026-02-10",
                "status": "open"
            },
            {
                "reference_id": "REF-002",
                "title": "Cloud Infrastructure Tender",
                "description": "AWS and Azure services required",
                "deadline_date": "2026-02-15",
                "status": "open"
            }
        ]
