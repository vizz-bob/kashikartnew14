import asyncio
import time
from datetime import datetime, timedelta
from app.core.database import AsyncSessionLocal
from app.models.tender import Tender
from app.models.keyword import TenderKeywordMatch
from sqlalchemy import select, func, and_

async def profile_stats():
    async with AsyncSessionLocal() as db:
        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        seven_days_ago = today_start - timedelta(days=7)
        fourteen_days_ago = today_start - timedelta(days=14)

        start = time.time()
        total_tenders = await db.scalar(select(func.count(Tender.id)).where(Tender.is_deleted == False))
        print(f"total_tenders: {total_tenders} took {time.time() - start:.2f}s")

        start = time.time()
        new_recent = await db.scalar(select(func.count(Tender.id)).where(and_(Tender.created_at >= seven_days_ago, Tender.is_deleted == False)))
        print(f"new_recent: {new_recent} took {time.time() - start:.2f}s")

        start = time.time()
        new_previous = await db.scalar(select(func.count(Tender.id)).where(and_(Tender.created_at >= fourteen_days_ago, Tender.created_at < seven_days_ago, Tender.is_deleted == False)))
        print(f"new_previous: {new_previous} took {time.time() - start:.2f}s")

        start = time.time()
        total_matches = await db.scalar(select(func.count(TenderKeywordMatch.id)))
        print(f"total_matches: {total_matches} took {time.time() - start:.2f}s")
        
        start = time.time()
        matched_recent = await db.scalar(select(func.count(func.distinct(TenderKeywordMatch.tender_id))).where(TenderKeywordMatch.created_at >= seven_days_ago))
        print(f"matched_recent: {matched_recent} took {time.time() - start:.2f}s")

if __name__ == "__main__":
    asyncio.run(profile_stats())
