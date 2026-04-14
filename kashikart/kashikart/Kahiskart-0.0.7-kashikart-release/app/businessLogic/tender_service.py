from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import hashlib
import logging
from datetime import datetime

from app.models.tender import Tender
from app.models.keyword import Keyword
from app.businessLogic.keyword_service import KeywordService
from app.businessLogic.notification_service import NotificationService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class TenderService:

    @staticmethod
    async def create_tender(
        db: AsyncSession,
        tender_data: Dict,
        source_id: int
    ) -> Optional[Tender]:

        # attach source
        tender_data["source_id"] = source_id

        # ---- STEP 1: CHECK DUPLICATE FIRST ----
        stmt = select(Tender).where(
            Tender.reference_id == tender_data["reference_id"],
            Tender.source_id == source_id,
            Tender.is_deleted == False
        )

        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(
                f"Tender {tender_data['reference_id']} already exists — skipping"
            )
            return None   # <-- IMPORTANT: skip instead of crashing

        # ---- STEP 2: CREATE NEW TENDER ----
        content = f"{tender_data.get('title', '')}{tender_data.get('description', '')}"
        tender_data["content_hash"] = hashlib.sha256(content.encode()).hexdigest()

        tender = Tender(**tender_data)
        db.add(tender)

        await db.flush()   # async flush

        # ---- STEP 3: MATCH KEYWORDS ----
        matched_keywords = await KeywordService.match_keywords(
            db,
            tender.title,
            tender.description
        )

        if matched_keywords:
            tender.matched_keywords = [k.id for k in matched_keywords]
            tender.keyword_match_count = len(matched_keywords)

        for keyword in matched_keywords:
            keyword.match_count += 1

        await NotificationService.send_keyword_match_notification(
            db, tender, matched_keywords
        )

        await db.commit()
        await db.refresh(tender)

        logger.info(
            f"Saved tender {tender.reference_id}"
        )

        return tender
    # @staticmethod
    # async def create_tender(db: AsyncSession, tender_data: Dict, source_id: int) -> Tender:


    #     # Generate content hash for change detection
    #     content = f"{tender_data.get('title', '')}{tender_data.get('description', '')}"
    #     content_hash = hashlib.sha256(content.encode()).hexdigest()

    #     tender_data['content_hash'] = content_hash

    #     # Create tender
    #     tender = Tender(**tender_data)
    #     db.add(tender)
    #     db.flush()  # Get ID without committing

    #     # Match keywords
    #     matched_keywords = KeywordService.match_keywords(
    #         db,
    #         tender.title,
    #         tender.description
    #     )

    #     if matched_keywords:
    #         tender.matched_keywords = [k.id for k in matched_keywords]
    #         tender.keyword_match_count = len(matched_keywords)

    #         # Update keyword match counts
    #         for keyword in matched_keywords:
    #             keyword.match_count += 1

    #         # Send notifications for matches
    #         NotificationService.send_keyword_match_notification(
    #             db, tender, matched_keywords
    #         )

    #     db.commit()
    #     db.refresh(tender)

    #     logger.info(f"Created tender: {tender.reference_id} with {tender.keyword_match_count} keyword matches")

    #     return tender

    @staticmethod
    def update_tender(db: Session, tender: Tender, update_data: Dict) -> Tender:


        # Check if content changed
        old_content = f"{tender.title}{tender.description or ''}"
        old_hash = hashlib.sha256(old_content.encode()).hexdigest()

        # Update fields
        for field, value in update_data.items():
            if value is not None:
                setattr(tender, field, value)

        # Recalculate hash
        new_content = f"{tender.title}{tender.description or ''}"
        new_hash = hashlib.sha256(new_content.encode()).hexdigest()

        if old_hash != new_hash:
            tender.content_hash = new_hash
            tender.version += 1

            # Re-match keywords if content changed
            matched_keywords = KeywordService.match_keywords(
                db,
                tender.title,
                tender.description
            )

            if matched_keywords:
                tender.matched_keywords = [k.id for k in matched_keywords]
                tender.keyword_match_count = len(matched_keywords)

        db.commit()
        db.refresh(tender)

        return tender

    @staticmethod
    def check_duplicate(db: Session, reference_id: str, source_id: int) -> Optional[Tender]:

        return db.query(Tender).filter(
            Tender.reference_id == reference_id,
            Tender.source_id == source_id,
            Tender.is_deleted == False
        ).first()

    @staticmethod
    def update_expired_tenders(db: Session) -> int:

        from datetime import date

        today = date.today()

        expired_count = db.query(Tender).filter(
            Tender.deadline_date < today,
            Tender.status != "expired",
            Tender.is_deleted == False
        ).update({"status": "expired"})

        db.commit()

        if expired_count > 0:
            logger.info(f"Marked {expired_count} tenders as expired")

        return expired_count

    @staticmethod
    def run_keyword_matching(db: Session, limit: int = 100):


        # Get recent tenders without keyword matches
        tenders = db.query(Tender).filter(
            Tender.keyword_match_count == 0,
            Tender.is_deleted == False
        ).order_by(Tender.created_at.desc()).limit(limit).all()

        matched_count = 0

        for tender in tenders:
            matched_keywords = KeywordService.match_keywords(
                db,
                tender.title,
                tender.description
            )

            if matched_keywords:
                tender.matched_keywords = [k.id for k in matched_keywords]
                tender.keyword_match_count = len(matched_keywords)
                matched_count += 1

                # Update keyword counts
                for keyword in matched_keywords:
                    keyword.match_count += 1

        db.commit()

        logger.info(f"Keyword matching completed: {matched_count}/{len(tenders)} tenders matched")

        return matched_count


def run_keyword_matching(db: Session):

    TenderService.run_keyword_matching(db)