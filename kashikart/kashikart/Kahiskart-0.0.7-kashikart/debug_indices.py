import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check():
    async with engine.connect() as conn:
        for table in ["tenders", "tender_keyword_matches", "notifications"]:
            print(f"\nTABLE: {table}")
            result = await conn.execute(text(f"SHOW INDEX FROM {table}"))
            for row in result.all():
                # row[2] index name, row[4] column name
                print(f"  - {row[2]} on {row[4]}")

if __name__ == "__main__":
    asyncio.run(check())
