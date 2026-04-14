import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        try:
            res = await db.execute(select(User))
            users = res.scalars().all()
            print(f"COUNT: {len(users)}")
            for u in users:
                print(f"User: {u.email}, Verified: {u.is_verified}")
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(check())
