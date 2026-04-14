import asyncio
import os
import sys
import traceback
from datetime import datetime, timedelta
from sqlalchemy import func, and_, desc, select
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.tender import Tender
from app.models.source import Source
from app.models.keyword import Keyword, TenderKeywordMatch
from app.models.notification import Notification

async def debug_stats():
    with open("dashboard_debug.txt", "w") as f:
        f.write("STARTING_DEBUG\n")
        async with AsyncSessionLocal() as db:
            try:
                res = await db.execute(select(User).limit(1))
                user = res.scalar_one_or_none()
                if not user:
                    f.write("NO_USER\n")
                    return
                
                f.write(f"USER: {user.email}\n")
                
                today_start = datetime.now().replace(hour=0, minute=0, second=0)
                thirty_days_ago = today_start - timedelta(days=30)

                f.write("QUERYING_KEYWORDS\n")
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
                f.write("FETCHING_ALL\n")
                # This is the line that might be failing
                data = result.all()
                f.write(f"DATA_LEN: {len(data)}\n")
                
                f.write("SUCCESS\n")
            except Exception as e:
                f.write(f"ERROR: {str(e)}\n")
                f.write(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(debug_stats())
