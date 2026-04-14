from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from app.scraping.base.scraper import BaseScraper
from app.scraping.utils.session_manager import SessionManager


class HTMLScraper(BaseScraper):
    async def scrape(self) -> List[Dict]:
        session = SessionManager.get_session(self.source)

        response = session.get(self.source.url, timeout=self.timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        tenders = []

        for el in soup.select(".tender-item"):
            tender = self._extract(el)
            if tender and self.validate_tender_data(tender):
                tenders.append(tender)

        return tenders

    def _extract(self, element) -> Optional[Dict]:
        title = self.clean_text(element.get_text())
        if not title:
            return None

        return {
            "title": title,
            "reference_id": self.extract_reference_id(title),
            "source_url": self.source.url,
        }
