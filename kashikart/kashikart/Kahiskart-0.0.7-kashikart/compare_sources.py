import asyncio
import pandas as pd
import os
import sys
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.source import Source
from sqlalchemy import select

async def compare_sources():
    # 1. Get sources from Excel
    file_path = 'uploads/All Source Web Links.xlsx'
    excel_sources = set()
    if os.path.exists(file_path):
        xl = pd.ExcelFile(file_path)
        for sheet_name in xl.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            for _, row in df.iterrows():
                data = row.to_dict()
                name = data.get('Source') or data.get('source') or data.get('City/Agency') or data.get('Name')
                url = data.get('Web Source Data Link (Links of Tender Release Sources)') or data.get('Column3 (Source Link 1)') or data.get('Column4') or data.get('URL') or data.get('Link')
                
                if name and url and not pd.isna(name) and not pd.isna(url):
                    excel_sources.add((str(name).strip().lower(), str(url).strip().lower()))
    
    # 2. Get sources from DB
    db_sources = set()
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Source))
        rows = res.scalars().all()
        for r in rows:
            db_sources.add((r.name.strip().lower(), r.url.strip().lower()))
            
    # 3. Compare
    missing = excel_sources - db_sources
    print(f"UNIQUE SOURCES IN EXCEL: {len(excel_sources)}")
    print(f"SOURCES IN DATABASE: {len(db_sources)}")
    print(f"SOURCES IN EXCEL BUT NOT IN DB: {len(missing)}")
    
    if len(missing) > 0:
        print("\nSAMPLE MISSING (First 5):")
        for i, (name, url) in enumerate(list(missing)[:5]):
            print(f"- {name} ({url})")

if __name__ == "__main__":
    asyncio.run(compare_sources())
