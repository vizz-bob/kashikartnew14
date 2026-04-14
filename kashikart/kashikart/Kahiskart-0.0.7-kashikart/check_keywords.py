import asyncio
import os
import sys
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.keyword import Keyword
from sqlalchemy import select, func

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(func.count(Keyword.id)))
        print(f"TOTAL KEYWORDS IN DATABASE: {res.scalar()}")

if __name__ == "__main__":
    asyncio.run(check())
