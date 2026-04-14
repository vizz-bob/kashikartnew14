import asyncio
from app.core.database import AsyncSessionLocal
from app.models.source import Source
from sqlalchemy import select, delete

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Source).where(Source.name.ilike('%Asian%')))
        sources = res.scalars().all()
        for s in sources:
            print(f"Deleting source: {s.name} (ID: {s.id})")
            await db.delete(s)
        
        await db.commit()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(run())
