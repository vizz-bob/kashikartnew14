import asyncio
import logging
from app.core.database import AsyncSessionLocal
from app.businessLogic.fetch_service import FetchService
from app.models import Source
from sqlalchemy import select

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_fetch():
    async with AsyncSessionLocal() as db:
        # Get our test source
        res = await db.execute(select(Source).where(Source.name == "Test HTML Source"))
        source = res.scalar_one_or_none()
        
        if not source:
            print("Test source not found! Run seed_source.py first.")
            return

        print(f"Starting fetch for source: {source.name} (type: {source.scraper_type})")
        fetch_service = FetchService(db)
        
        try:
            # Trigger fetch
            results = await fetch_service.fetch_from_source(source.id)
            print(f"Fetch completed!")
            print(f"RESULTS: {results}")
            
            # Commit changes
            await db.commit()
            
        except Exception as e:
            print(f"Fetch failed with error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fetch())
