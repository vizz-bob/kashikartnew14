import asyncio
from app.core.database import AsyncSessionLocal
from app.models.fetch_log import FetchLog
from sqlalchemy import select, desc

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(FetchLog)
            .where(FetchLog.source_id.in_([7, 8, 9]))
            .order_by(desc(FetchLog.created_at))
            .limit(10)
        )
        logs = res.scalars().all()
        for log in logs:
            print(f"ID: {log.id}, SourceID: {log.source_id}, Status: {log.status}, Tenders: {log.tenders_found}, Msg: {log.message}")

if __name__ == "__main__":
    asyncio.run(run())
