import asyncio
import os
import sys
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import verify_password
from sqlalchemy import select

async def check_login():
    email = "admin@gmail.com"
    password = "Admin@123"
    
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.email == email))
        user = res.scalar_one_or_none()
        
        if not user:
            print(f"User {email} not found")
            return
            
        is_correct = verify_password(password, user.hashed_password)
        print(f"User: {user.email}")
        print(f"Password Check: {is_correct}")
        print(f"Verified: {user.is_verified}")
        print(f"Active: {user.is_active}")
        print(f"Blocked: {user.is_blocked}")

if __name__ == "__main__":
    asyncio.run(check_login())
