import asyncio
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.source import Source
from sqlalchemy import select, update

async def add_sample_configs():
    async with AsyncSessionLocal() as db:
        # Get first 3 active HTML sources
        res = await db.execute(
            select(Source.id, Source.name)
            .where(Source.scraper_type == 'html', Source.is_active == True)
            .limit(3)
        )
        sources = res.fetchall()
        
        sample_config = {
            "container_selector": ".tender-item, .bid-notice, .procurement-item, tr, .card, .list-group-item",
            "selectors": {
                "title": {"selector": "h3, h4, .title, [class*='title'], [class*='name']"},
                "reference_id": {"selector": ".ref, .id, [class*='id'], [class*='ref']", "type": "attribute", "attribute": "data-id"},
                "description": ".desc, .description, p",
                "deadline_date": ".deadline, .due-date, .closing, [class*='date']",
                "agency_name": ".agency, .authority, .buyer"
            }
        }
        
        for sid, name in sources:
            stmt = update(Source).where(Source.id == sid).values(selector_config=sample_config)
            await db.execute(stmt)
            print(f"Added sample config to source {sid} '{name}'")
        
        await db.commit()
        print("✅ Sample configs added!")

if __name__ == "__main__":
    asyncio.run(add_sample_configs())

