import asyncio
from app.core.database import AsyncSessionLocal
from app.models.source import Source
from sqlalchemy import select
import json

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Source).where(Source.name == "Manual Test Source"))
        sources = res.scalars().all()
        for s in sources:
            print(f"--- ID: {s.id} ---")
            print(f"URL: {s.url}")
            print(f"Scraper: {s.scraper_type}")
            print(f"Config: {json.dumps(s.selector_config, indent=2)}")
            print(f"Last Success: {s.last_success_at}")
            print(f"Failures: {s.consecutive_failures}")

if __name__ == "__main__":
    asyncio.run(run())
