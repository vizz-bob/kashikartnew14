from sqlalchemy.orm import Session
from typing import List, Optional
import re
import logging
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tender import Tender
from app.models.keyword import Keyword

logger = logging.getLogger(__name__)


class KeywordService:

    @staticmethod
    async def match_keywords(db: AsyncSession, tender: Tender) -> List[Keyword]:
        """
        Match keywords in headings AND content.
        Headings: title, reference_id, agency_name, agency_location (higher priority)
        Content: description
        """
        # Get all active keywords
        result = await db.execute(select(Keyword).where(Keyword.is_active == True))
        keywords = result.scalars().all()

        if not keywords:
            return []

        # Headings text (title, ref, agency, location)
        headings_text = f"{tender.title or ''} {tender.reference_id or ''} {tender.agency_name or ''} {tender.agency_location or ''}".lower()
        # Content text
        content_text = tender.description or ''
        search_texts = [headings_text, content_text]

        matched = []

        for keyword in keywords:
            keyword_lower = keyword.keyword.lower()
            # Create pattern for whole word matching
            pattern = r'\b' + re.escape(keyword_lower) + r'\b'

            # Check if matches in any text
            if any(re.search(pattern, text.lower()) for text in search_texts):
                matched.append(keyword)
                logger.debug(f"Keyword '{keyword.keyword}' matched (headings/content)")

        def pr_val(k):
            try:
                if isinstance(k.priority, str) and k.priority.lower().startswith("p"):
                    return int(k.priority[1:])
                return int(k.priority or 0)
            except Exception:
                return 0

        # Sort by priority (11 highest -> 1 lowest)
        matched.sort(key=lambda k: -pr_val(k))

        return matched

    @staticmethod
    def get_keywords_by_category(db: Session, category: str) -> List[Keyword]:
        return db.query(Keyword).filter(
            Keyword.category == category,
            Keyword.is_active == True
        ).all()

    @staticmethod
    def get_high_priority_keywords(db: Session) -> List[Keyword]:
        # Treat priority p9-p11 as high
        return db.query(Keyword).filter(
            Keyword.priority.in_(["p9", "p10", "p11"]),
            Keyword.is_active == True
        ).all()

    @staticmethod
    def bulk_create_keywords(db: Session, keywords_data: List[dict]) -> List[Keyword]:
        keywords = []
        for data in keywords_data:
            existing = db.query(Keyword).filter(
                Keyword.keyword.ilike(data['keyword'])
            ).first()
            if not existing:
                keyword = Keyword(**data)
                db.add(keyword)
                keywords.append(keyword)
        db.commit()
        logger.info(f"Created {len(keywords)} new keywords")
        return keywords
