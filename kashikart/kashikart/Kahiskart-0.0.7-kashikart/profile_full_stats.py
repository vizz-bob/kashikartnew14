import asyncio
import time
from datetime import datetime, timedelta
from app.core.database import AsyncSessionLocal
from app.models.tender import Tender
from app.models.keyword import Keyword, TenderKeywordMatch
from app.models.source import Source
from app.models.notification import Notification
from sqlalchemy import select, func, and_, desc

async def profile_full_stats():
    async with AsyncSessionLocal() as db:
        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        seven_days_ago = today_start - timedelta(days=7)
        fourteen_days_ago = today_start - timedelta(days=14)
        thirty_days_ago = today_start - timedelta(days=30)
        user_id = 1 # Assuming a user ID for profiling

        queries = [
            ("total_tenders", select(func.count(Tender.id)).where(Tender.is_deleted == False)),
            ("new_recent", select(func.count(Tender.id)).where(and_(Tender.created_at >= seven_days_ago, Tender.is_deleted == False))),
            ("new_previous", select(func.count(Tender.id)).where(and_(Tender.created_at >= fourteen_days_ago, Tender.created_at < seven_days_ago, Tender.is_deleted == False))),
            ("total_matches", select(func.count(TenderKeywordMatch.id))),
            ("matched_recent", select(func.count(func.distinct(TenderKeywordMatch.tender_id))).where(TenderKeywordMatch.created_at >= seven_days_ago)),
            ("matched_previous", select(func.count(func.distinct(TenderKeywordMatch.tender_id))).where(and_(TenderKeywordMatch.created_at >= fourteen_days_ago, TenderKeywordMatch.created_at < seven_days_ago))),
            ("active_sources", select(func.count(Source.id)).where(Source.is_active == True)),
            ("total_sources", select(func.count(Source.id))),
            ("total_notifications", select(func.count(Notification.id)).where(and_(Notification.user_id == user_id, Notification.is_read == False, Notification.created_at >= today_start))),
            ("top_keywords", select(Keyword.keyword, Keyword.category, func.count(TenderKeywordMatch.id)).join(TenderKeywordMatch).where(TenderKeywordMatch.created_at >= thirty_days_ago).group_by(Keyword.id, Keyword.keyword, Keyword.category).order_by(desc(func.count(TenderKeywordMatch.id))).limit(5))
        ]

        print(f"{'Query':<25} | {'Count':<10} | {'Time (s)':<10}")
        print("-" * 50)

        for name, query in queries:
            start = time.time()
            if "top_keywords" in name:
                res = await db.execute(query)
                count = len(res.all())
            else:
                count = await db.scalar(query)
            elapsed = time.time() - start
            print(f"{name:<25} | {str(count):<10} | {elapsed:.4f}")

if __name__ == "__main__":
    asyncio.run(profile_full_stats())
