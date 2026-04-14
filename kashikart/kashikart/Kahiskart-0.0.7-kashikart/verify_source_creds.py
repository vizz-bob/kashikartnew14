import asyncio
import os
import sys
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.source import Source, LoginType
from sqlalchemy import select

async def verify():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Source).where(Source.login_required == True).limit(5))
        sources = res.scalars().all()
        print(f"SOURCES WITH LOGIN REQUIRED: {len(sources)}")
        for s in sources:
            print(f"- {s.name}: {s.username} / {s.password} ({s.login_type})")

if __name__ == "__main__":
    asyncio.run(verify())
