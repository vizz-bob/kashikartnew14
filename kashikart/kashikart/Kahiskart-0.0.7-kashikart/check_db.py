import asyncio
from app.core.database import AsyncSessionLocal
from app.models.tender import Tender
from sqlalchemy import select, func

async def check():
    async with AsyncSessionLocal() as db:
        count = await db.scalar(select(func.count(Tender.id)))
        print(f"Total Tenders: {count}")

if __name__ == "__main__":
    asyncio.run(check())
