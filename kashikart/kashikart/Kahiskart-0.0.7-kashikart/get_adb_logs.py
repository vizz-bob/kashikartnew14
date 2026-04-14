import asyncio
from app.core.database import AsyncSessionLocal
from app.models.fetch_log import FetchLog
from sqlalchemy import select, desc

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(FetchLog)
            .where(FetchLog.source_name.ilike('%Asian Development%'))
            .order_by(desc(FetchLog.created_at))
            .limit(5)
        )
        logs = res.scalars().all()
        for log in logs:
            print(f"ID: {log.id}, Status: {log.status}, Tenders: {log.tenders_found}, Msg: {log.message}, Created: {log.created_at}")

if __name__ == "__main__":
    asyncio.run(run())
