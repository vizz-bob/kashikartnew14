import asyncio
from sqlalchemy import text
from app.core.database import engine

async def clear():
    async with engine.connect() as conn:
        print("Clearing tenders and matches...")
        await conn.execute(text("DELETE FROM tender_keyword_matches"))
        await conn.execute(text("DELETE FROM tenders"))
        await conn.commit()
    print("Done")

if __name__ == "__main__":
    asyncio.run(clear())
