import asyncio
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
from app.core.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        emails = ["admin@gmail.com", "gauravkumar@gmail.com"]
        for email in emails:
            res = await db.execute(select(User).where(User.email == email))
            user = res.scalar_one_or_none()
            if user:
                print(f"FOUND: {email} | VERIFIED: {user.is_verified} | ACTIVE: {user.is_active}")
            else:
                print(f"NOT FOUND: {email}")

if __name__ == "__main__":
    asyncio.run(check())
