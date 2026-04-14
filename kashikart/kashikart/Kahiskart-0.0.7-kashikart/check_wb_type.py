import asyncio
from app.core.database import AsyncSessionLocal
from app.models.source import Source
from sqlalchemy import select

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Source).where(Source.name.ilike('%World Bank%')))
        s = res.scalar_one_or_none()
        if s:
            print(f"Name: {s.name}")
            print(f"Scraper: {s.scraper_type}")
            print(f"URL: {s.url}")
        else:
            print("Not found")

if __name__ == "__main__":
    asyncio.run(run())
