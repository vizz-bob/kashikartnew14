import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check():
    async with engine.connect() as conn:
        print("--- fetch_logs schema ---")
        res = await conn.execute(text("DESCRIBE fetch_logs"))
        for row in res:
            print(row)
        
        print("\n--- fetch_logs status values ---")
        try:
            res = await conn.execute(text("SHOW CREATE TABLE fetch_logs"))
            print(res.fetchone()[1])
        except Exception as e:
            print(f"Error getting create table: {e}")

if __name__ == "__main__":
    asyncio.run(check())
