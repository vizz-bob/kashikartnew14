import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import func, and_, desc, select
from sqlalchemy.orm import joinedload
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.tender import Tender
from app.models.source import Source
from app.models.keyword import Keyword, TenderKeywordMatch
from app.models.notification import Notification

async def debug_stats():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).limit(1))
        current_user = res.scalar_one_or_none()
        if not current_user:
            print("USER_NOT_FOUND")
            return

        print(f"DEBUG: Processing stats for {current_user.email}")
        
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0)
            thirty_days_ago = today_start - timedelta(days=30)

            print("DEBUG: Executing top keywords query")
            stmt = select(
                Keyword.keyword,
                Keyword.category,
                func.count(TenderKeywordMatch.id).label("match_count")
            ).join(TenderKeywordMatch).where(
                TenderKeywordMatch.created_at >= thirty_days_ago
            ).group_by(
                Keyword.id, Keyword.keyword, Keyword.category
            ).order_by(
                desc(func.count(TenderKeywordMatch.id))
            ).limit(5)
            
            result = await db.execute(stmt)
            print("DEBUG: Fetching all results")
            keywords_data = result.all()
            print(f"DEBUG: Found {len(keywords_data)} keywords")
            
            for k in keywords_data:
                print(f"Keyword: {k[0]}, Count: {k[2]}")
                
            print("DEBUG: Stats calculation successful")
            
        except Exception as e:
            print(f"DEBUG: ERROR occurred: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_stats())
