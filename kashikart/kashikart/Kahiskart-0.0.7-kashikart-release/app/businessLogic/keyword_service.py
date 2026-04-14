from sqlalchemy.orm import Session
from typing import List, Optional
import re
import logging
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.keyword import Keyword , KeywordPriority

logger = logging.getLogger(__name__)


class KeywordService:

    @staticmethod
    async def match_keywords(db: AsyncSession, title: str, description: Optional[str] = None) -> List[Keyword]:


        # Get all active keywords
        # keywords = db.query(Keyword).filter(Keyword.is_active == True).all()
        result = await db.execute(select(Keyword).where(Keyword.is_active == True))
        keywords = result.scalars().all()

        if not keywords:
            return []

        # Combine title and description for matching
        content = f"{title or ''} {description or ''}".lower()

        matched = []

        for keyword in keywords:
            # Create word boundary pattern for whole word matching
            pattern = r'\b' + re.escape(keyword.keyword.lower()) + r'\b'

            if re.search(pattern, content):
                matched.append(keyword)
                logger.debug(f"Keyword matched: {keyword.keyword}")

        # Sort by priority (high first)
        # priority_order = {"high": 0, "medium": 1, "low": 2}
        # matched.sort(key=lambda k: priority_order.get(k.priority.value, 3))
        priority_order = {
            KeywordPriority.HIGH.value: 0,
            KeywordPriority.MEDIUM.value: 1,
            KeywordPriority.LOW.value: 2,
        }

        matched.sort(key=lambda k: priority_order.get(k.priority.value, 3))


        return matched

    @staticmethod
    def get_keywords_by_category(db: Session, category: str) -> List[Keyword]:

        return db.query(Keyword).filter(
            Keyword.category == category,
            Keyword.is_active == True
        ).all()

    @staticmethod
    def get_high_priority_keywords(db: Session) -> List[Keyword]:

        return db.query(Keyword).filter(
            Keyword.priority == "high",
            Keyword.is_active == True
        ).all()

    @staticmethod
    def bulk_create_keywords(db: Session, keywords_data: List[dict]) -> List[Keyword]:

        keywords = []

        for data in keywords_data:
            # Check if exists
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