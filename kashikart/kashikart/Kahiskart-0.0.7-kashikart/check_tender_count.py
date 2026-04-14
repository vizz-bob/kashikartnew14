import asyncio
import os
import sys
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.tender import Tender
from sqlalchemy import select, func

async def count_tenders():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(func.count()).select_from(Tender))
        count = res.scalar()
        print(f"TOTAL TENDERS IN DATABASE: {count}")

if __name__ == "__main__":
    asyncio.run(count_tenders())
