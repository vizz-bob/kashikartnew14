import asyncio
import logging
import sys
from app.core.database import AsyncSessionLocal
from app.businessLogic.fetch_service import FetchService
from app.models.source import Source

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def trigger_adb_fetch():
    async with AsyncSessionLocal() as db:
        # ADB source ID is 11
        source = await db.get(Source, 11)
        if not source:
            print("ADB Source not found")
            return
            
        print(f"Triggering fetch for {source.name} (ID: {source.id}, Type: {source.scraper_type})")
        fetch_service = FetchService(db)
        
        try:
            results = await fetch_service.fetch_from_source(source.id)
            print(f"Fetch completed: {results}")
             # Results are committed inside fetch_from_source
        except Exception as e:
            print(f"Fetch failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(trigger_adb_fetch())
