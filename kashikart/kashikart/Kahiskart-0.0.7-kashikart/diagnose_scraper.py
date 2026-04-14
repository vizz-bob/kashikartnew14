import asyncio
import sys
import os
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from sqlalchemy import select, text
from app.models.source import Source
from app.models.fetch_log import FetchLog

async def diagnose():
    async with AsyncSessionLocal() as db:
        print("=== TENDER FETCH DIAGNOSIS ===\n")
        
        # 1. Active HTML sources
        res = await db.execute(
            select(Source.id, Source.name, Source.url, Source.scraper_type, Source.selector_config)
            .where(Source.scraper_type == 'html', Source.is_active == True)
            .limit(5)
        )
        sources = res.fetchall()
        print("1. ACTIVE HTML SOURCES:")
        for s in sources:
            print(f"  ID:{s.id} | {s.name} | {s.url}")
            print(f"     Config: {s.selector_config}")
        print()
        
        # 2. Recent fetch logs
        res = await db.execute(
            select(FetchLog.source_name, FetchLog.status, FetchLog.tenders_found, FetchLog.message, FetchLog.created_at)
            .order_by(FetchLog.created_at.desc())
            .limit(10)
        )
        logs = res.fetchall()
        print("2. RECENT FETCH LOGS:")
        for log in logs:
            print(f"  {log.created_at} | {log.source_name} | {log.status} | Found:{log.tenders_found} | {log.message[:100]}")
        print()
        
        # 3. Source count by scraper_type
        res = await db.execute(text("""
            SELECT scraper_type, COUNT(*) as count, SUM(total_tenders) as total_tenders 
            FROM sources WHERE is_active = 1 GROUP BY scraper_type
        """))
        types = res.fetchall()
        print("3. SOURCE TYPES (Active):")
        for t in types:
            print(f"  {t.scraper_type}: {t.count} sources, {t.total_tenders} total tenders")
        print()
        
        # 4. Check if scheduler is configured for scraping
        print("4. RECOMMENDED NEXT STEPS:")
        print("   a) python run_scraper_debug.py")
        print("   b) python add_sample_source_config.py") 
        print("   c) python run_scraper_debug.py  # Tests FIRST source")
        print("   d) Check /api/fetch/logs for results")

if __name__ == "__main__":
    asyncio.run(diagnose())

