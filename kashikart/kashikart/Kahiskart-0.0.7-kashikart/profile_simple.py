import asyncio
import time
from datetime import datetime, timedelta
from app.core.database import AsyncSessionLocal
from app.models.tender import Tender
from app.models.keyword import Keyword, TenderKeywordMatch
from app.models.source import Source
from app.models.notification import Notification
from sqlalchemy import select, func, and_, desc

async def run_profile():
    async with AsyncSessionLocal() as db:
        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        seven_days_ago = today_start - timedelta(days=7)
        fourteen_days_ago = today_start - timedelta(days=14)
        thirty_days_ago = today_start - timedelta(days=30)
        user_id = 1

        print("Starting Profiling...")
        
        # 1. Total Tenders
        s = time.time()
        res = await db.scalar(select(func.count(Tender.id)).where(Tender.is_deleted == False))
        print(f"Total Tenders Count: {res} | Time: {time.time()-s:.2f}s")

        # 2. New Recent
        s = time.time()
        res = await db.scalar(select(func.count(Tender.id)).where(and_(Tender.created_at >= seven_days_ago, Tender.is_deleted == False)))
        print(f"New Recent Count: {res} | Time: {time.time()-s:.2f}s")

        # 3. Matches Recent (DISTINCT)
        s = time.time()
        res = await db.scalar(select(func.count(func.distinct(TenderKeywordMatch.tender_id))).where(TenderKeywordMatch.created_at >= seven_days_ago))
        print(f"Matched Recent Count: {res} | Time: {time.time()-s:.2f}s")

        # 4. Top Keywords
        s = time.time()
        res = await db.execute(select(Keyword.keyword, Keyword.category, func.count(TenderKeywordMatch.id)).join(TenderKeywordMatch).where(TenderKeywordMatch.created_at >= thirty_days_ago).group_by(Keyword.id, Keyword.keyword, Keyword.category).order_by(desc(func.count(TenderKeywordMatch.id))).limit(5))
        rows = res.all()
        print(f"Top Keywords: {len(rows)} | Time: {time.time()-s:.2f}s")

if __name__ == "__main__":
    asyncio.run(run_profile())
