import asyncio
from app.core.database import AsyncSessionLocal
from app.models.source import Source
from sqlalchemy import select, delete

async def run():
    async with AsyncSessionLocal() as db:
        # Delete sources with the exact name "Manual Test Source"
        res = await db.execute(select(Source).where(Source.name == "Manual Test Source"))
        sources = res.scalars().all()
        
        for s in sources:
            print(f"Deleting manual source: {s.name} (ID: {s.id})")
            await db.delete(s)
        
        # Also handle potential duplicates or variations like "Test Site" if requested, 
        # but sticking to "Manual Test Source" for now as per request.
        
        await db.commit()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(run())
