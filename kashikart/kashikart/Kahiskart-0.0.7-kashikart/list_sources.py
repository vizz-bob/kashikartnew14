import asyncio
from app.core.database import AsyncSessionLocal
from app.models.source import Source
from sqlalchemy import select

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Source))
        sources = res.scalars().all()
        for s in sources:
            print(f"ID: {s.id}, Name: {s.name}, Type: {s.scraper_type}, Tenders: {s.total_tenders}")

if __name__ == "__main__":
    asyncio.run(run())
