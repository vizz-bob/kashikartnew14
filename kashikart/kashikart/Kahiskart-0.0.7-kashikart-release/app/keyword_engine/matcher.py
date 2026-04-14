import re
from typing import List, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.keyword import Keyword, TenderKeywordMatch
from app.models.tender import Tender
from app.utils.logger import setup_logger

logger = setup_logger()


class KeywordMatcher:
    """
    Intelligent keyword matching engine.
    Matches keywords against tender title, description, and documents.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.keywords_cache = None

    async def load_keywords(self):
        """Load active keywords into cache"""
        query = select(Keyword).where(Keyword.is_active == True)
        result = await self.db.execute(query)
        self.keywords_cache = result.scalars().all()
        logger.info(f"Loaded {len(self.keywords_cache)} active keywords")

    async def match_tender(self, tender: Tender) -> List[Tuple[Keyword, str]]:
        """
        Match keywords against a tender.

        Args:
            tender: Tender object to match

        Returns:
            List of tuples (Keyword, match_location)
        """
        if not self.keywords_cache:
            await self.load_keywords()

        matches = []

        # Prepare text to search
        title = tender.title or ""
        description = tender.description or ""
        document_text = tender.document_text or ""

        # Match each keyword
        for keyword in self.keywords_cache:
            match_location = self._match_keyword(
                keyword,
                title,
                description,
                document_text
            )

            if match_location:
                matches.append((keyword, match_location))

        return matches

    def _match_keyword(
            self,
            keyword: Keyword,
            title: str,
            description: str,
            document: str
    ) -> str:
        """
        Check if keyword matches in any location.

        Returns:
            Match location ('title', 'description', 'document') or empty string
        """
        keyword_text = keyword.keyword

        # Case sensitivity
        if not keyword.is_case_sensitive:
            keyword_text = keyword_text.lower()
            title = title.lower()
            description = description.lower()
            document = document.lower()

        # Whole word matching
        if keyword.match_whole_word:
            pattern = r'\b' + re.escape(keyword_text) + r'\b'

            if re.search(pattern, title):
                return 'title'
            if re.search(pattern, description):
                return 'description'
            if re.search(pattern, document):
                return 'document'
        else:
            # Substring matching
            if keyword_text in title:
                return 'title'
            if keyword_text in description:
                return 'description'
            if keyword_text in document:
                return 'document'

        return ''

    async def save_matches(
            self,
            tender: Tender,
            matches: List[Tuple[Keyword, str]]
    ):
        """
        Save keyword matches to database.

        Args:
            tender: Tender object
            matches: List of (Keyword, location) tuples
        """
        for keyword, location in matches:
            # Check if match already exists
            existing_query = select(TenderKeywordMatch).where(
                TenderKeywordMatch.tender_id == tender.id,
                TenderKeywordMatch.keyword_id == keyword.id
            )
            result = await self.db.execute(existing_query)
            existing = result.scalar_one_or_none()

            if not existing:
                # Create new match
                match = TenderKeywordMatch(
                    tender_id=tender.id,
                    keyword_id=keyword.id,
                    match_location=location
                )
                self.db.add(match)

                # Update keyword statistics
                keyword.match_count += 1
                keyword.last_match_date = tender.created_at

                logger.info(
                    f"Matched keyword '{keyword.keyword}' "
                    f"in tender {tender.id} ({location})"
                )

        # Mark tender as matched if any keywords matched
        if matches:
            tender.is_matched = True

        await self.db.commit()

    async def match_and_save(self, tender: Tender) -> int:
        """
        Match keywords and save results.

        Args:
            tender: Tender to match

        Returns:
            Number of keywords matched
        """
        matches = await self.match_tender(tender)
        await self.save_matches(tender, matches)
        return len(matches)

    async def batch_match_tenders(self, tender_ids: List[int]) -> Dict[int, int]:
        """
        Match multiple tenders in batch.

        Args:
            tender_ids: List of tender IDs

        Returns:
            Dictionary mapping tender_id to match count
        """
        results = {}

        for tender_id in tender_ids:
            tender = await self.db.get(Tender, tender_id)
            if tender:
                match_count = await self.match_and_save(tender)
                results[tender_id] = match_count

        return results