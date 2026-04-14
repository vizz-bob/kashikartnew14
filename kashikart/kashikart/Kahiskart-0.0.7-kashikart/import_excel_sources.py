import asyncio
import os
import sys

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.excel_raw import ExcelFile
from app.businessLogic.excel_processor_sync import ExcelProcessorSync
from app.routers.excel_control import create_sources_from_excel
from sqlalchemy import select

async def run_import():
    """
    Utility script to import sources from the master Excel sheet.
    This script:
    1. Registers the file in the systems Excel tracker.
    2. Parses the Excel rows into the raw storage table.
    3. Detects and creates new Source records for the scraping engine.
    """
    # Path to the master file
    file_path = os.path.abspath("uploads/All Source Web Links.xlsx").replace("\\", "/")
    print(f"[*] Target file: {file_path}")

    if not os.path.exists(file_path):
        print(f"[!] File not found at {file_path}. Please ensure the file is in the uploads directory.")
        return

    # 1. Register the file
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(ExcelFile).where(ExcelFile.file_path == file_path))
        excel_file = res.scalar_one_or_none()
        
        if not excel_file:
            print("[*] Registering new Excel file entry...")
            excel_file = ExcelFile(file_path=file_path)
            db.add(excel_file)
            await db.commit()
            await db.refresh(excel_file)
        else:
            print("[*] Excel file already registered.")
        
        file_id = excel_file.id

    # 2. Ingest Rows
    print("[*] Ingesting Excel rows...")
    try:
        ExcelProcessorSync.process_file(file_id, file_path)
    except Exception as e:
        print(f"[!] Ingestion error: {e}")
        return

    # 3. Create Sources
    print("[*] Updating Source records...")
    async with AsyncSessionLocal() as db:
        result = await create_sources_from_excel(db)
        print(f"[+] Success!")
        print(f"    - Created: {result.get('created', 0)} new sources")
        print(f"    - Skipped: {result.get('skipped', 0)} existing or duplicate sources")

if __name__ == "__main__":
    asyncio.run(run_import())
