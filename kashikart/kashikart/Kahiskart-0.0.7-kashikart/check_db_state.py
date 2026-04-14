import asyncio
import logging
from sqlalchemy import text
from app.core.database import engine
import app.models

# KILL LOGGING
logging.getLogger('sqlalchemy').setLevel(logging.ERROR)

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT count(*) FROM sources"))
        sc = res.scalar()
        res = await conn.execute(text("SELECT count(*) FROM tenders"))
        tc = res.scalar()
        res = await conn.execute(text("SELECT count(*) FROM tender_keyword_matches"))
        mc = res.scalar()
        
        print(f"--- DATABASE STATE ---")
        print(f"Sources: {sc}")
        print(f"Tenders: {tc}")
        print(f"Keyword Matches: {mc}")
        
        if tc > 0:
            print("\n--- RECENT TENDERS ---")
            res = await conn.execute(text("SELECT reference_id, title, created_at FROM tenders ORDER BY created_at DESC LIMIT 5"))
            for t in res:
                print(f"[{t[0]}] {t[1]} (Created: {t[2]})")

        if mc > 0:
            print("\n--- RECENT MATCHES ---")
            res = await conn.execute(text("""
                SELECT t.reference_id, k.keyword, m.match_location 
                FROM tender_keyword_matches m
                JOIN tenders t ON m.tender_id = t.id
                JOIN keywords k ON m.keyword_id = k.id
                ORDER BY m.created_at DESC LIMIT 5
            """))
            for m in res:
                print(f"Tender: {m[0]} | Keyword: {m[1]} | Location: {m[2]}")

if __name__ == "__main__":
    asyncio.run(check())
