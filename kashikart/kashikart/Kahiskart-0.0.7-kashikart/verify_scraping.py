import asyncio
from app.core.database import engine
from sqlalchemy import text

async def verify_scraping():
    async with engine.connect() as conn:
        # Check Tenders
        tenders_count = await conn.execute(text("SELECT count(*) FROM tenders"))
        count = tenders_count.scalar()
        
        # Check Sources
        sources_result = await conn.execute(text("SELECT id, name, scraper_type, total_tenders FROM sources"))
        sources = sources_result.fetchall()
        
        # Check Latest Logs
        logs_result = await conn.execute(text("SELECT source_name, status, message, created_at FROM fetch_logs ORDER BY created_at DESC LIMIT 5"))
        logs = logs_result.fetchall()
        
        print("\n--- SCRAPING VERIFICATION REPORT ---")
        print(f"Total Tenders found in Database: {count}")
        
        print("\nActive Sources in Database:")
        for s in sources:
            print(f"- ID: {s[0]} | Name: {s[1]} | Type: {s[2]} | Tenders Found: {s[3]}")
            
        print("\nRecent Scraping Logs:")
        for log in logs:
            print(f"[{log[3]}] {log[0]} -> {log[1]}: {log[2]}")
        print("------------------------------------\n")

if __name__ == "__main__":
    asyncio.run(verify_scraping())
