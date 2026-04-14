import asyncio
import logging
from sqlalchemy import text
from app.core.database import engine

logging.getLogger('sqlalchemy').setLevel(logging.ERROR)

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT id, keyword, match_whole_word, is_case_sensitive FROM keywords"))
        print("--- KEYWORDS ---")
        for row in res:
            print(f"ID: {row[0]} | KW: {row[1]} | Whole: {row[2]} | Sensitive: {row[3]}")
        print("--- END ---")

if __name__ == "__main__":
    asyncio.run(check())
