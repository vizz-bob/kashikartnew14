from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import logging
import re
import hashlib
from datetime import datetime, date

from app.models.source import Source
from app.core.config import settings
from app.scraping.utils import parse_date, clean_text

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    def __init__(self, source: Source):
        self.source = source
        self.timeout = getattr(settings, "REQUEST_TIMEOUT", 30)
        self.user_agent = getattr(settings, "USER_AGENT", "Mozilla/5.0")

    @abstractmethod
    async def scrape(self) -> List[Dict]:
        pass

    # ---------- SHARED HELPERS ----------

    def normalize_date(self, value: str) -> Optional[date]:
        return parse_date(value)

    def clean_text(self, value: str) -> str:
        return clean_text(value)

    def extract_reference_id(self, text: str) -> str:
        patterns = [
            r'[A-Z]{2,}-\d{4,}',
            r'RFP[-\s]?\d+',
            r'IFB[-\s]?\d+',
            r'\d{6,}',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        return hashlib.md5(text.encode()).hexdigest()[:12]

    def validate_tender_data(self, tender: Dict) -> bool:
        for field in ("title", "reference_id"):
            if not tender.get(field):
                return False
        return True
