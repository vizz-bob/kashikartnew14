import asyncio
import os
import sys

# Silence noisy libraries
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.routers.dashboard import get_dashboard_stats
from sqlalchemy import select

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).limit(1))
        user = res.scalar_one_or_none()
        if not user:
            print("NO_USER_FOUND")
            return
        
        try:
            stats = await get_dashboard_stats(db=db, current_user=user)
            print("STATS_SUCCESS")
            print(stats)
        except Exception as e:
            print("STATS_ERROR")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
