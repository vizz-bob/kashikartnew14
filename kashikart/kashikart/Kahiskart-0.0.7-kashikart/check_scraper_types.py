import asyncio
from app.core.database import AsyncSessionLocal
from app.models.source import Source
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Source.scraper_type).distinct())
        types = [r[0] for r in res.all()]
        print('Current scraper types:', types)

if __name__ == "__main__":
    asyncio.run(check())
