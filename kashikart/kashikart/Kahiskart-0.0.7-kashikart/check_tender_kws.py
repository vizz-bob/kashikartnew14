import asyncio
import os
import sys
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.routers.dashboard import get_recent_tenders

async def check_api():
    async with AsyncSessionLocal() as db:
        # We need a mock user if get_recent_tenders ends on it, but wait
        # get_recent_tenders(limit, db, current_user)
        # Actually I can just run the query logic inside.
        
        from app.models.tender import Tender
        from app.models.source import Source
        from app.models.keyword import TenderKeywordMatch
        from sqlalchemy import select, desc
        from sqlalchemy.orm import joinedload
        
        result = await db.execute(
            select(Tender, Source.name.label("source_name"))
            .outerjoin(Source, Tender.source_id == Source.id)
            .options(
                joinedload(Tender.keyword_matches).joinedload(TenderKeywordMatch.keyword)
            )
            .where(Tender.is_deleted == False)
            .order_by(desc(Tender.created_at))
            .limit(10)
        )
        
        rows = result.unique().all()
        for t, sname in rows:
            kws = [m.keyword.keyword for m in t.keyword_matches]
            print(f"TENDER: {t.title[:50]} | KWS: {kws}")

if __name__ == "__main__":
    asyncio.run(check_api())
