import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check():
    async with engine.connect() as conn:
        with open("indices_final_debug.txt", "w") as f:
            for table in ["tenders", "tender_keyword_matches"]:
                f.write(f"\nTABLE: {table}\n")
                result = await conn.execute(text(f"SHOW INDEX FROM {table}"))
                indices = result.all()
                for idx in indices:
                    # Column 2 is Key_name, Column 4 is Column_name
                    f.write(f"  - Index: {idx[2]} on {idx[4]}\n")

if __name__ == "__main__":
    asyncio.run(check())
