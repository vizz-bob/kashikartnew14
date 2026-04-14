import asyncio
from app.core.database import AsyncSessionLocal
from app.models import Source, Tender, FetchLog # Import all to avoid mapper errors
from app.models.source import SourceStatus, LoginType
from sqlalchemy import select

async def seed():
    async with AsyncSessionLocal() as db:
        # Check if source exists
        res = await db.execute(select(Source).where(Source.name == "Test HTML Source"))
        if res.scalar_one_or_none():
            print("Source exists")
        else:
            source = Source(
                name="Test HTML Source",
                url="https://www.google.com/search?q=tenders", # Just a test URL
                scraper_type="html",
                is_active=True,
                status=SourceStatus.ACTIVE,
                login_type=LoginType.PUBLIC,
                selector_config={
                    "item_selector": "div.g",
                    "title_selector": "h3",
                    "link_selector": "a"
                }
            )
            db.add(source)
            print("Source added")

        await db.commit()

if __name__ == "__main__":
    asyncio.run(seed())
