import asyncio
import os
import sys
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.source import Source
from sqlalchemy import select, func

async def count_sources():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(func.count()).select_from(Source))
        count = res.scalar()
        print(f"TOTAL SOURCES IN DATABASE: {count}")
        
        # Also list some to be sure
        res = await db.execute(select(Source).limit(5))
        sources = res.scalars().all()
        for s in sources:
            print(f"- {s.name} ({s.url})")

if __name__ == "__main__":
    asyncio.run(count_sources())
