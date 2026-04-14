import asyncio
import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import func, and_, desc, select
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.tender import Tender
from app.models.source import Source
from app.models.keyword import Keyword, TenderKeywordMatch
from app.models.notification import Notification

def log(msg):
    os.write(1, (str(msg) + "\n").encode('utf-8'))

async def debug_stats():
    log("STARTING_DEBUG_STATS_V3")
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).limit(1))
        current_user = res.scalar_one_or_none()
        if not current_user:
            log("USER_NOT_FOUND")
            return

        log(f"DEBUG_USER: {current_user.email}")
        
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0)
            thirty_days_ago = today_start - timedelta(days=30)

            log("EXECUTING_TOP_KEYWORDS_QUERY")
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
            log("FETCHING_RESULTS")
            keywords_data = result.all()
            log(f"FOUND: {len(keywords_data)}")
            
            log("SUCCESS")
            
        except Exception as e:
            log(f"ERROR: {e}")
            import traceback
            log(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(debug_stats())
