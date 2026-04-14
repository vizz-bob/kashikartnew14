import asyncio
import sys
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.businessLogic.fetch_service import FetchService
from app.models.source import Source
from sqlalchemy import select
import os

async def debug_scrapers():
    async with AsyncSessionLocal() as db:
        # Get first 3 active HTML sources
        res = await db.execute(
            select(Source)
            .where(Source.scraper_type == 'html', Source.is_active == True)
            .order_by(Source.id)
            .limit(3)
        )
        sources = res.scalars().all()
        
        print(f"Found {len(sources)} active HTML sources:")
        for s in sources:
            print(f"  ID:{s.id} '{s.name}' URL:{s.url}")
            print(f"  selector_config: {s.selector_config}")
            print()
        
        if sources:
            print("Testing scrape on first source...")
            fetch_service = FetchService(db)
            try:
                result = await fetch_service.fetch_from_source(sources[0].id)
                print("Scrape result:", result)
            except Exception as e:
                print("Scrape error:", str(e))

if __name__ == "__main__":
    asyncio.run(debug_scrapers())

