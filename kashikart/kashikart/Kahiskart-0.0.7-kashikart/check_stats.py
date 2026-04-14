import asyncio
import os
import sys
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.source import Source
from sqlalchemy import select

async def check_stats():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Source))
        sources = res.scalars().all()
        
        total = len(sources)
        active = len([s for s in sources if s.is_active])
        excel_type = len([s for s in sources if s.scraper_type == 'excel'])
        
        print(f"TOTAL SOURCES: {total}")
        print(f"ACTIVE SOURCES: {active}")
        print(f"EXCEL SCRAPER TYPE: {excel_type}")
        
        if total > 0:
            print("\nLAST 5 ADDED SOURCES:")
            sorted_s = sorted(sources, key=lambda x: x.id, reverse=True)
            for s in sorted_s[:5]:
                print(f"- ID: {s.id} | {s.name} | {s.url}")

if __name__ == "__main__":
    asyncio.run(check_stats())
