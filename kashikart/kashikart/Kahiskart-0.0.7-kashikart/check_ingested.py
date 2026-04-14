import asyncio
import os
import sys
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.excel_raw import ExcelRowRaw
from sqlalchemy import select, func

async def check_ingested_rows():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(func.count()).select_from(ExcelRowRaw))
        count = res.scalar()
        print(f"TOTAL ROWS IN EXCELROWRAW: {count}")
        
        if count > 0:
            res = await db.execute(select(ExcelRowRaw).limit(10))
            rows = res.scalars().all()
            for r in rows:
                print(f"ID: {r.id} | SHEET: {r.sheet_id} | DATA: {str(r.row_data)[:100]}")

if __name__ == "__main__":
    asyncio.run(check_ingested_rows())
