import asyncio
import os
import sys
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        try:
            res = await db.execute(select(User))
            users = res.scalars().all()
            output = f"COUNT: {len(users)}\n"
            for u in users:
                output += f"User: {u.email}, Verified: {u.is_verified}, Superuser: {u.is_superuser}\n"
            
            with open("users_debug_output.txt", "w") as f:
                f.write(output)
            print("Done writing to users_debug_output.txt")
        except Exception as e:
            with open("users_debug_output.txt", "w") as f:
                f.write(f"ERROR: {e}")
            print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(check())
