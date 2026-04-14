import asyncio
import logging
from sqlalchemy import text
from app.core.database import engine

# FORCE KILL LOGS
logging.getLogger('sqlalchemy').setLevel(logging.ERROR)
logging.getLogger('aiomysql').setLevel(logging.ERROR)

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT count(*) FROM tender_keyword_matches"))
        count = res.scalar()
        print(f"--- MATCH VERIFICATION ---")
        print(f"TOTAL_MATCHES: {count}")
        
        if count > 0:
            res = await conn.execute(text("""
                SELECT t.reference_id, k.keyword, m.match_location 
                FROM tender_keyword_matches m
                JOIN tenders t ON m.tender_id = t.id
                JOIN keywords k ON m.keyword_id = k.id
            """))
            for row in res:
                print(f"MATCH: {row[0]} -> {row[1]} ({row[2]})")
        print(f"--- END ---")

if __name__ == "__main__":
    asyncio.run(check())
