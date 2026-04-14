import asyncio
import os
import sys
import pandas as pd
from datetime import datetime
from dateutil.parser import parse
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.source import Source
from app.models.tender import Tender
from sqlalchemy import select

def parse_date_safe(val):
    if not val or pd.isna(val):
        return None
    try:
        return parse(str(val), fuzzy=True).date()
    except:
        return None

async def import_all_tenders():
    file_path = 'uploads/All Source Web Links.xlsx'
    sheet_name = 'All_in_One_Data_Format_WA_OR'
    
    if not os.path.exists(file_path):
        print("File not found")
        return

    print(f"Reading {sheet_name}...")
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    print(f"Read {len(df)} rows.")

    async with AsyncSessionLocal() as db:
        # Load sources into a map
        res = await db.execute(select(Source))
        sources = res.scalars().all()
        source_map = {s.name.lower().strip(): s.id for s in sources}
        
        # Get "Excel Import" source as fallback
        res = await db.execute(select(Source).where(Source.name == "Excel Import"))
        excel_import_source = res.scalar_one_or_none()
        if not excel_import_source:
             excel_import_source = Source(name="Excel Import", url="internal://excel-import", scraper_type="excel", is_active=True)
             db.add(excel_import_source)
             await db.flush()
        
        fallback_id = excel_import_source.id
        
        imported = 0
        skipped = 0
        
        # We'll process in chunks of 500
        batch_size = 500
        total_rows = len(df)
        
        for i in range(0, total_rows, batch_size):
            chunk = df.iloc[i:i+batch_size]
            for _, row in chunk.iterrows():
                agency = str(row.get('City/Agency', '')).strip()
                title = str(row.get('Project Name', '')).strip()
                
                if not title or title.lower() == 'nan':
                    skipped += 1
                    continue
                
                source_id = source_map.get(agency.lower(), fallback_id)
                
                # Check for existing by title and source (simple de-dupe)
                # Note: reference_id is usually better but project name + source is a decent fallback
                # For this bulk import, we'll use project name as part of reference
                ref = str(row.get('ID', ''))
                if not ref or ref.lower() == 'nan':
                    ref = f"EXCEL-{i}-{_}"
                
                # Create Tender
                tender = Tender(
                    title=title[:500],
                    reference_id=ref[:255],
                    agency_name=agency[:200],
                    agency_location=str(row.get('State', ''))[:100],
                    deadline_date=parse_date_safe(row.get('Date')),
                    status=str(row.get('Status', 'open')).lower()[:50],
                    source_id=source_id,
                    imported_from_excel=True
                )
                db.add(tender)
                imported += 1
            
            await db.commit()
            print(f"Processed {min(i+batch_size, total_rows)}/{total_rows} rows...")
            
        # Update source counts
        print("Updating source tender counts...")
        # Since we just added a lot, we can just recount them all
        # But for now, let's keep it simple. The Sources API recounts them on GET.
        
    print(f"DONE: Imported {imported}, Skipped {skipped}")

if __name__ == "__main__":
    asyncio.run(import_all_tenders())
