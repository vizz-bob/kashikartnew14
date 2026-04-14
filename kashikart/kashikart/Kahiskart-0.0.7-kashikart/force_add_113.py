import asyncio
import pandas as pd
import os
import sys
from datetime import datetime
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.source import Source
from sqlalchemy import select

async def add_113_sources():
    file_path = 'uploads/All Source Web Links.xlsx'
    sheet_name = 'Source Links FL WA OR'
    
    if not os.path.exists(file_path):
        print("File not found")
        return

    df = pd.read_excel(file_path, sheet_name=sheet_name)
    
    added = 0
    skipped = 0
    
    async with AsyncSessionLocal() as db:
        for _, row in df.iterrows():
            data = row.to_dict()
            name = (data.get('Source') or data.get('source'))
            url = (data.get('Web Source Data Link (Links of Tender Release Sources)') or data.get('Link'))
            
            if pd.isna(name) or pd.isna(url):
                continue
                
            name = str(name).strip()
            url = str(url).strip()
            
            # Check if exists
            res = await db.execute(select(Source).where(Source.name == name))
            existing = res.scalar_one_or_none()
            
            if existing:
                skipped += 1
                continue
            
            # Add new source
            login_req = str(data.get('User Login Required?', '')).lower() == 'yes'
            user = str(data.get('User', '')) if not pd.isna(data.get('User')) else None
            password = str(data.get('Password', '')) if not pd.isna(data.get('Password')) else None
            remarks = str(data.get('Remarks', '')) if not pd.isna(data.get('Remarks')) else ""
            
            new_source = Source(
                name=name,
                url=url,
                scraper_type='excel',
                status='ACTIVE',
                is_active=True,
                login_required=login_req,
                password=password,
                # Note: The Source model might not have a 'username' field, checking model
                description=f"Auto-imported from sheet '{sheet_name}'. {remarks}"
            )
            
            db.add(new_source)
            added += 1
            
        await db.commit()
        
    print(f"DONE: Added {added}, Skipped {skipped} (already exist)")

if __name__ == "__main__":
    asyncio.run(add_113_sources())
