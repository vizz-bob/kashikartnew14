import asyncio
from app.core.database import AsyncSessionLocal
from app.models.source import Source

async def run():
    async with AsyncSessionLocal() as db:
        s = await db.get(Source, 11)
        if s:
            s.scraper_type = 'portal'
            # Also update URL to tenders page if it's more relevant, 
            # though /procurement redirected there usually.
            # s.url = "https://www.adb.org/projects/tenders"
            await db.commit()
            print("Updated source 11 to use portal scraper")
        else:
            print("Source 11 not found")

if __name__ == "__main__":
    asyncio.run(run())
