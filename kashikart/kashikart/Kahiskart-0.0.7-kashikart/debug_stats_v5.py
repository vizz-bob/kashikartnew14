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
from app.routers.dashboard import get_dashboard_stats

async def debug_stats():
    with open("dashboard_debug_full.txt", "w") as f:
        f.write("STARTING_DEBUG_FULL\n")
        async with AsyncSessionLocal() as db:
            try:
                res = await db.execute(select(User).limit(1))
                user = res.scalar_one_or_none()
                if not user:
                    f.write("NO_USER\n")
                    return
                
                f.write(f"USER: {user.email}\n")
                
                # Call the actual router function
                result = await get_dashboard_stats(db=db, current_user=user)
                f.write(f"RESULT: {str(result)[:100]}\n")
                f.write("SUCCESS_FULL\n")
            except Exception as e:
                f.write(f"ERROR: {str(e)}\n")
                f.write(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(debug_stats())
