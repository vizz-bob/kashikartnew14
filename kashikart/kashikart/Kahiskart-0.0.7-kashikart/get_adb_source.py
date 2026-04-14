import asyncio
from app.core.database import AsyncSessionLocal
from app.models.source import Source
from sqlalchemy import select
import json

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Source).where(Source.name.ilike('%Asian Development%')))
        s = res.scalar_one_or_none()
        if s:
            print(f"ID: {s.id}")
            print(f"Name: {s.name}")
            print(f"URL: {s.url}")
            print(f"Selector Config: {json.dumps(s.selector_config, indent=2)}")
        else:
            print("Not found")

if __name__ == "__main__":
    asyncio.run(run())
