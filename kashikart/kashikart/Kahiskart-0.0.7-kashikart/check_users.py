import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select

async def check():
    users_data = []
    try:
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(User))
            users = res.scalars().all()
            for u in users:
                users_data.append(f"Email: {u.email}, Verified: {u.is_verified}")
    except Exception as e:
        print(f"Error: {e}")
    
    print(f"Total users found: {len(users_data)}")
    for data in users_data:
        print(data)

if __name__ == "__main__":
    asyncio.run(check())
