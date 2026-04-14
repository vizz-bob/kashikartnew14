import asyncio
from sqlalchemy import text
from app.core.database import engine

async def add_indices():
    async with engine.begin() as conn:
        print("Checking/Adding indices...")
        
        # 1. Tender is_deleted
        try:
            await conn.execute(text("CREATE INDEX ix_tenders_is_deleted ON tenders(is_deleted)"))
            print("Added ix_tenders_is_deleted")
        except Exception as e:
            print(f"Skipped ix_tenders_is_deleted (maybe exists?): {str(e)}")

        # 2. TenderKeywordMatch created_at
        try:
            await conn.execute(text("CREATE INDEX ix_tender_keyword_matches_created_at ON tender_keyword_matches(created_at)"))
            print("Added ix_tender_keyword_matches_created_at")
        except Exception as e:
            print(f"Skipped ix_tender_keyword_matches_created_at (maybe exists?): {str(e)}")

if __name__ == "__main__":
    asyncio.run(add_indices())
