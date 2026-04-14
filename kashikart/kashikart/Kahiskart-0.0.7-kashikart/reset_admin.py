import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select

async def update_admin():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.email == "admin@gmail.com"))
        user = res.scalar_one_or_none()
        if user:
            user.hashed_password = get_password_hash("admin123")
            user.is_verified = True
            user.is_active = True
            await db.commit()
            print("Admin password updated to 'admin123'")
        else:
            print("Admin user not found")

if __name__ == "__main__":
    asyncio.run(update_admin())
