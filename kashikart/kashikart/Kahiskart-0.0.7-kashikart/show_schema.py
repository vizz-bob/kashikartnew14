import asyncio
from sqlalchemy import text
from app.core.database import engine

async def show_schema():
    async with engine.connect() as conn:
        for table in ["tenders", "tender_keyword_matches", "keywords", "notifications"]:
            print(f"\n--- {table} ---")
            result = await conn.execute(text(f"SHOW CREATE TABLE {table}"))
            row = result.fetchone()
            if row:
                print(row[1])

if __name__ == "__main__":
    asyncio.run(show_schema())
