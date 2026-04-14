import asyncio
from app.core.database import AsyncSessionLocal
from app.models.source import Source
from app.scheduler.jobs import fetch_single_source_job
from sqlalchemy import select

async def update_and_refresh_adb():
    async with AsyncSessionLocal() as db:
        stmt = select(Source).where(Source.name.ilike("%Asian Development%"))
        res = await db.execute(stmt)
        src = res.scalar()

        if not src:
            print("ADB source not found.")
            return

        print(f"Updating Source ID: {src.id} ({src.name})")

        # Set to HTML scraper since `cloudscraper` now handles the bot protection
        src.scraper_type = "html"
        # From the manual soup test, we can use these CSS Selectors
        src.selector_config = {
            "container_selector": ".item",
            "selectors": {
                "title": ".item-title a, .title a",
                "reference_id": ".item-title a, .title a",
                "description": ".item-summary, .summary",
                "published_date": ".date, .item-meta",
                "agency_name": ".agency, .item-meta"
            }
        }

        await db.commit()
        print("Config updated. Starting fetch...")

        await fetch_single_source_job(src.id)

        await db.refresh(src)
        print(f"FETCH DONE. TENDERS: {src.total_tenders}")

if __name__ == "__main__":
    asyncio.run(update_and_refresh_adb())
