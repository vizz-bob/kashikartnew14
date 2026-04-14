import asyncio
import os
import sys
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.tender import Tender
from app.models.source import Source
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Source).where(Source.name == "Excel Import"))
        source = res.scalar_one_or_none()
        if not source:
            print("Source 'Excel Import' not found")
            return
            
        res = await db.execute(select(Tender).where(Tender.source_id == source.id))
        tenders = res.scalars().all()
        print(f"Tenders assigned to 'Excel Import': {len(tenders)}")

if __name__ == "__main__":
    asyncio.run(check())
