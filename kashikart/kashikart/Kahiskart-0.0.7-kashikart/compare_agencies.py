import asyncio
import os
import sys
import pandas as pd
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.source import Source
from sqlalchemy import select

async def compare():
    # Get DB source names
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Source))
        db_names = {s.name.lower().strip() for s in res.scalars().all()}
    
    # Get Excel agency names
    file_path = 'uploads/All Source Web Links.xlsx'
    df = pd.read_excel(file_path, sheet_name='All_in_One_Data_Format_WA_OR', usecols=['City/Agency'])
    excel_names = {str(n).lower().strip() for n in df['City/Agency'].dropna().unique()}
    
    matches = db_names.intersection(excel_names)
    print(f"DB SOURCES: {len(db_names)}")
    print(f"EXCEL AGENCIES: {len(excel_names)}")
    print(f"EXACT MATCHES: {len(matches)}")
    
    if len(excel_names - db_names) > 0:
        print("\nSAMPLE MISSING FROM DB (First 5):")
        for n in list(excel_names - db_names)[:5]:
            print(f"- {n}")

if __name__ == "__main__":
    asyncio.run(compare())
