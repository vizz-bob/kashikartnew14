import asyncio, logging, sys, os
logging.disable(logging.CRITICAL)
sys.path.append(os.getcwd())

from sqlalchemy import text

async def test():
    from app.core.database import engine
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("DB CONNECTION: SUCCESS")
            result = await conn.execute(text("SHOW TABLES"))
            tables = result.fetchall()
            print(f"Tables found: {len(tables)}")
            for t in tables:
                print(f"  - {t[0]}")
    except Exception as e:
        print(f"DB CONNECTION: FAILED - {e}")

asyncio.run(test())
