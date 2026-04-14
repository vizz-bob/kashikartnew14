import asyncio
from app.core.database import AsyncSessionLocal
from app.models.source import Source
from sqlalchemy import select, func

async def check():
    async with AsyncSessionLocal() as db:
        count = await db.scalar(select(func.count(Source.id)))
        print(f"\nTOTAL SOURCES IN DATABASE: {count}")
        
        # Also check a few recent ones
        res = await db.execute(select(Source.name, Source.url).order_by(Source.id.desc()).limit(5))
        print("\nMOST RECENTLY ADDED SOURCES:")
        for row in res.all():
            print(f"- {row[0]}: {row[1]}")

if __name__ == "__main__":
    asyncio.run(check())
