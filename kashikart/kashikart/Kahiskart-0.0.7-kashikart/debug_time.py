import asyncio
from app.core.database import AsyncSessionLocal
from app.models.fetch_log import FetchLog
from sqlalchemy import select, desc
from datetime import datetime, timedelta

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(FetchLog).order_by(desc(FetchLog.created_at)).limit(1))
        log = res.scalar_one_or_none()
        with open('time_comparison.txt', 'w') as f:
            if log:
                f.write(f"Raw DB created_at: {log.created_at}\n")
                f.write(f"Current UTC: {datetime.utcnow()}\n")
                f.write(f"Current IST: {datetime.utcnow() + timedelta(hours=5, minutes=30)}\n")
            else:
                f.write("No fetch logs found.\n")
        print("Comparison written to time_comparison.txt")

if __name__ == "__main__":
    asyncio.run(check())
