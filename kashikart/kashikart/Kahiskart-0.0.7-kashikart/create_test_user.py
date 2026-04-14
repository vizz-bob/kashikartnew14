import asyncio
import os
import sys
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select

async def create_test_user():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.email == "test@test.com"))
        if res.scalar_one_or_none():
            print("User test@test.com already exists")
            return
            
        user = User(
            email="test@test.com",
            hashed_password=get_password_hash("Password@123"),
            full_name="Test User",
            is_verified=True,
            is_active=True
        )
        db.add(user)
        await db.commit()
        print("User test@test.com created with Password@123")

if __name__ == "__main__":
    asyncio.run(create_test_user())
