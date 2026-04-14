import asyncio
import os
import sys

# Add the current directory to sys.path to import app
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select

async def create_admin():
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(User).where(User.email == "admin@gmail.com"))
            user = result.scalar_one_or_none()
            if not user:
                user = User(
                    email="admin@gmail.com",
                    hashed_password=get_password_hash("Admin@123"),
                    full_name="Admin User",
                    is_verified=True,
                    is_active=True,
                    is_superuser=True
                )
                session.add(user)
                print("Admin user created: admin@gmail.com / Admin@123")
            else:
                user.hashed_password = get_password_hash("Admin@123")
                user.is_verified = True
                user.is_active = True
                print("Admin user password updated: Admin@123")
            await session.commit()
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(create_admin())
