from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from app.scraping.base.scraper import BaseScraper
from app.scraping.utils.session_manager import SessionManager
from datetime import date
import logging

logger = logging.getLogger(__name__)


class HTMLScraper(BaseScraper):
    def _selector_css(self, selector_value) -> Optional[str]:
        """Accept both plain selector strings and object-style selector configs."""
        if isinstance(selector_value, str):
            return selector_value
        if isinstance(selector_value, dict):
            return selector_value.get("selector")
        return None

    def _extract_value(self, element, selector_value):
        css = self._selector_css(selector_value)
        if not css:
            return None

        found = element.select_one(css)
        if not found:
            return None

        if isinstance(selector_value, dict) and selector_value.get("type") == "attribute":
            attr_name = selector_value.get("attribute") or "href"
            return self.clean_text(found.get(attr_name) or "")

        return self.clean_text(found.get_text())

    async def scrape(self) -> List[Dict]:
        session = SessionManager.get_session(self.source)

        import asyncio
        response = await asyncio.to_thread(session.get, self.source.url, timeout=self.timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        print(f"DEBUG: Soup length for {self.source.name}: {len(soup.get_text())}")
        tenders = []
        
        config = self.source.selector_config or {}
        container_selector = config.get("container_selector")
        
        if not container_selector:
            logger.warning(f"No container selector for source {self.source.name}. Using whole page as one tender.")
            # Fallback: Treat the whole page as a single potential tender if no container is defined
            tender = self._extract(soup, config)
            if tender and self.validate_tender_data(tender):
                tenders.append(tender)
            return tenders
            
        elements = soup.select(container_selector)
        logger.info(f"Found {len(elements)} elements using selector {container_selector}")
        
        for el in elements:
            try:
                tender = self._extract(el, config)
                if tender and self.validate_tender_data(tender):
                    tenders.append(tender)
            except Exception as e:
                logger.error(f"Error extracting tender: {e}")
                
        return tenders

    def _extract(self, element, config: Dict) -> Optional[Dict]:
        selectors = config.get("selectors", {})
        
        def get_val(key):
            sel = selectors.get(key)
            if not sel:
                return None
            return self._extract_value(element, sel)

        # Fallback to page title or context if get_val fails
        fallback_title = self.clean_text(element.get_text()[:200])
        if not fallback_title and hasattr(element, "title") and element.title:
            fallback_title = self.clean_text(element.title.string)
            
        title = get_val("title") or fallback_title or f"Tender from {self.source.name}"
        
        ref_id = (get_val("reference_id") or self.extract_reference_id(f"{self.source.id}_{title}"))[:450]
        
        return {
            "title": title,
            "reference_id": ref_id,
            "description": get_val("description"),
            "agency_name": get_val("agency_name") or self.source.name,
            "source_url": self.source.url,
            "published_date": self.normalize_date(get_val("published_date")),
            "deadline_date": self.normalize_date(get_val("deadline_date")),
        }
