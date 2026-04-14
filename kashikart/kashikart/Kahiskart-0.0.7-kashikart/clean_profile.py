import asyncio
import time
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, desc, text
from app.core.database import AsyncSessionLocal, engine
from app.models.tender import Tender
from app.models.keyword import Keyword, TenderKeywordMatch
from app.models.source import Source
from app.models.notification import Notification

# Disable all logging for this script
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

async def profile():
    async with AsyncSessionLocal() as db:
        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        seven_days_ago = today_start - timedelta(days=7)
        fourteen_days_ago = today_start - timedelta(days=14)
        thirty_days_ago = today_start - timedelta(days=30)
        user_id = 1

        queries = [
            ("Total Tenders", select(func.count(Tender.id)).where(Tender.is_deleted == False)),
            ("New (7d)", select(func.count(Tender.id)).where(and_(Tender.created_at >= seven_days_ago, Tender.is_deleted == False))),
            ("New (Prev 7d)", select(func.count(Tender.id)).where(and_(Tender.created_at >= fourteen_days_ago, Tender.created_at < seven_days_ago, Tender.is_deleted == False))),
            ("Total Matches", select(func.count(TenderKeywordMatch.id))),
            ("Matches (7d)", select(func.count(func.distinct(TenderKeywordMatch.tender_id))).where(TenderKeywordMatch.created_at >= seven_days_ago)),
            ("Matches (Prev 7d)", select(func.count(func.distinct(TenderKeywordMatch.tender_id))).where(and_(TenderKeywordMatch.created_at >= fourteen_days_ago, TenderKeywordMatch.created_at < seven_days_ago))),
            ("Active Sources", select(func.count(Source.id)).where(Source.is_active == True)),
            ("Total Notifications", select(func.count(Notification.id)).where(and_(Notification.user_id == user_id, Notification.is_read == False, Notification.created_at >= today_start))),
            ("Top Keywords (30d)", select(Keyword.keyword, Keyword.category, func.count(TenderKeywordMatch.id)).join(TenderKeywordMatch).where(TenderKeywordMatch.created_at >= thirty_days_ago).group_by(Keyword.id, Keyword.keyword, Keyword.category).order_by(desc(func.count(TenderKeywordMatch.id))).limit(5))
        ]

        print("\n" + "="*60)
        print(f"{'Query Name':<25} | {'Count/Size':<10} | {'Time (s)':<10}")
        print("-" * 60)

        for name, query in queries:
            start = time.time()
            if "Top Keywords" in name:
                res = await db.execute(query)
                val = len(res.all())
            else:
                val = await db.scalar(query)
            elapsed = time.time() - start
            print(f"{name:<25} | {str(val):<10} | {elapsed:.4f}")
        print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(profile())
