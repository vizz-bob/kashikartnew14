import asyncio
from app.core.database import AsyncSessionLocal
from app.models.source import Source

async def run():
    async with AsyncSessionLocal() as db:
        s = await db.get(Source, 11)
        if s:
            print(f"Scraper Type: {s.scraper_type}")
            print(f"URL: {s.url}")
        else:
            print("Source 11 not found")

if __name__ == "__main__":
    asyncio.run(run())
