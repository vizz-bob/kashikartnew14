from typing import List, Dict
from app.scraping.base.scraper import BaseScraper
from app.scraping.utils.session_manager import SessionManager
from app.scraping.utils.web_scraper_executor import WebScraperExecutor
import json

class WebScraperIOScraper(BaseScraper):
    """
    Scraper implementation that uses Web Scraper.io sitemaps.
    The sitemap JSON is stored in source.selector_config.
    """
    async def scrape(self) -> List[Dict]:
        if not self.source.selector_config:
            raise ValueError(f"No sitemap configuration found for source: {self.source.name}")

        # The selector_config is already a dict (JSON column in DB)
        # Convert to string for the executor or modify executor to accept dict
        sitemap_json = json.dumps(self.source.selector_config)
        executor = WebScraperExecutor(sitemap_json)

        session = SessionManager.get_session(self.source)
        response = session.get(self.source.url, timeout=self.timeout)
        response.raise_for_status()

        scraped_items = executor.execute(response.text)
        
        # Map scraped items to Tender model format
        tenders = []
        for item in scraped_items:
            tender = self._map_to_tender(item)
            if tender and self.validate_tender_data(tender):
                tenders.append(tender)
                
        return tenders

    def _map_to_tender(self, data: Dict) -> Dict:
        # Standard field mapping - Web Scraper.io IDs should match these or we map them
        return {
            "title": data.get("title") or data.get("name") or "Untitled Tender",
            "reference_id": data.get("reference_id") or data.get("id") or self.extract_reference_id(data.get("title", "")),
            "description": data.get("description") or data.get("details"),
            "deadline_date": data.get("deadline") or data.get("date"),
            "source_url": self.source.url,
            "agency_name": data.get("agency") or self.source.name
        }
