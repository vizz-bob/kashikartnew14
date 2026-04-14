import asyncio
from datetime import datetime
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.routers.dashboard import get_dashboard_stats

async def test_stats():
    async with AsyncSessionLocal() as db:
        # Get first user
        res = await db.execute(select(User).limit(1))
        user = res.scalar_one_or_none()
        if not user:
            print("No user found")
            return
        
        print(f"Testing stats for user: {user.email}")
        try:
            stats = await get_dashboard_stats(db=db, current_user=user)
            print(f"Stats result: {stats}")
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_stats())
