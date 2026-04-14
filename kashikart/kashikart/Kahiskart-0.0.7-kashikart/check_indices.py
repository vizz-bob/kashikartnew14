import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check_indices():
    async with engine.connect() as conn:
        for table in ["tenders", "tender_keyword_matches", "notifications"]:
            print(f"\n--- Indices for {table} ---")
            result = await conn.execute(text(f"SHOW INDEX FROM {table}"))
            for row in result:
                print(f"Index: {row[2]}, Column: {row[4]}")

if __name__ == "__main__":
    asyncio.run(check_indices())
