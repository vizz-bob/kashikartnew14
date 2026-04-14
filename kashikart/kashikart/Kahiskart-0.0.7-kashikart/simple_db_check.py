import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check():
    print("START")
    async with engine.connect() as conn:
        print("CONNECTED")
        r = await conn.execute(text("SELECT count(*) FROM sources"))
        print(f"SOURCES COUNT: {r.scalar()}")
        r = await conn.execute(text("SELECT count(*) FROM tenders"))
        print(f"TENDERS COUNT: {r.scalar()}")
    print("END")

if __name__ == "__main__":
    asyncio.run(check())
