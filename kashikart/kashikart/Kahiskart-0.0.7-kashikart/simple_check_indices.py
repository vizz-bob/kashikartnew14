import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check():
    async with engine.connect() as conn:
        with open("indices_final.txt", "w") as f:
            for table in ["tenders", "tender_keyword_matches", "notifications"]:
                f.write(f"\nTABLE: {table}\n")
                result = await conn.execute(text(f"SHOW INDEX FROM {table}"))
                for row in result:
                    f.write(f"Index: {row[2]}, Column: {row[4]}\n")

if __name__ == "__main__":
    asyncio.run(check())
