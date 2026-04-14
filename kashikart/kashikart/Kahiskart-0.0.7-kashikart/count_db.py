import asyncio
import os
import sys
sys.path.append(os.getcwd())
from app.core.database import AsyncSessionLocal
from app.models.keyword import Keyword
from sqlalchemy import select, func

async def count_keywords():
    print("Connecting to database...")
    try:
        async with AsyncSessionLocal() as db:
            print("Session created. Executing count...")
            stmt = select(func.count(Keyword.id))
            result = await db.execute(stmt)
            count = result.scalar()
            print(f"Total Keywords found: {count}")

            # sample
            print("Fetching sample keywords...")
            stmt2 = select(Keyword).limit(5)
            res = await db.execute(stmt2)
            for kw in res.scalars():
                print(f"- {kw.keyword} ({kw.category})")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(count_keywords())
