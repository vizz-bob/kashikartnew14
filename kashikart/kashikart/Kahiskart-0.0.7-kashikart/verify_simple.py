import asyncio
import os
from sqlalchemy import text
from app.core.database import engine

async def verify():
    async with engine.connect() as conn:
        print("\n=== SYSTEM VERIFICATION ===")
        
        # 1. Tenders count
        tenders = await conn.execute(text("SELECT count(*) FROM tenders"))
        t_count = tenders.scalar()
        print(f"[*] Tenders in Database: {t_count}")
        
        # 2. Sources count
        sources = await conn.execute(text("SELECT count(*) FROM sources"))
        s_count = sources.scalar()
        print(f"[*] Sources in Database: {s_count}")
        
        # 3. Check for specific success logs
        logs = await conn.execute(text("SELECT count(*) FROM fetch_logs WHERE status='success'"))
        l_count = logs.scalar()
        print(f"[*] Successful scraping runs: {l_count}")
        
        if t_count == 0:
            print("[!] WARNING: No tenders found. Scraping may not have run or failed.")
        else:
            print("[+] SUCCESS: Tenders are being populated!")

        # 4. Show last 3 logs
        recent = await conn.execute(text("SELECT source_name, status, message FROM fetch_logs ORDER BY created_at DESC LIMIT 3"))
        print("\n--- Recent Logs ---")
        for row in recent:
            print(f"- {row[0]} | {row[1]} | {row[2][:50]}...")
        
        print("===========================\n")

if __name__ == "__main__":
    asyncio.run(verify())
