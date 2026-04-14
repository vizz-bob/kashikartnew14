import asyncio
from app.core.database import engine
from sqlalchemy import text

async def debug_system():
    async with engine.connect() as conn:
        print("\n--- DEBUG: DB STATE ---")
        
        # 1. Sources
        sources = await conn.execute(text("SELECT id, name, scraper_type, url FROM sources"))
        s_list = sources.fetchall()
        print(f"Sources in DB ({len(s_list)}):")
        for s in s_list:
            print(f"  - {s[0]}: {s[1]} ({s[2]}) | URL: {s[3]}")
            
        # 2. Tenders
        tenders = await conn.execute(text("SELECT count(*) FROM tenders"))
        print(f"\nTotal Tenders: {tenders.scalar()}")
        
        # 3. Last Scrape Logs
        logs = await conn.execute(text("SELECT source_name, status, message, created_at FROM fetch_logs ORDER BY id DESC LIMIT 5"))
        print("\nLatest Scraping Logs:")
        for l in logs.fetchall():
            print(f"  [{l[3]}] {l[0]}: {l[1]} | {l[2][:100]}")
            
        print("-----------------------\n")

if __name__ == "__main__":
    asyncio.run(debug_system())
