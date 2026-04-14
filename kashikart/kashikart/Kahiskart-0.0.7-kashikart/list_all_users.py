import asyncio
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

from app.core.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select

async def list_users():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User))
        users = res.scalars().all()
        print(f"FOUND {len(users)} USERS:")
        for u in users:
            print(f"ID: {u.id} | EMAIL: {u.email} | VERIFIED: {u.is_verified} | ACTIVE: {u.is_active} | BLOCKED: {u.is_blocked}")

if __name__ == "__main__":
    asyncio.run(list_users())
