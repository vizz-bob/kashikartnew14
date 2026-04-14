import asyncio
import os
import sys

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.core.sync_database import SyncSessionLocal
from app.models.excel_raw import ExcelFile
from app.businessLogic.excel_processor_sync import ExcelProcessorSync
from app.routers.excel_control import create_sources_from_excel
from sqlalchemy import select

async def run_import():
    # 1. Path to the file
    # Ensure it's the absolute path and formatted correctly for the DB
    file_path = os.path.abspath("uploads/All Source Web Links.xlsx").replace("\\", "/")
    print(f"[*] Target file: {file_path}")

    # 2. Register the file in the database (Async)
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
        print(f"[+] File ID: {file_id}")

    # 3. Process the file (Parsing rows into ExcelRowRaw table)
    # This uses the project's built-in sync processor
    print("[*] Starting Excel row ingestion (this may take a moment)...")
    try:
        ExcelProcessorSync.process_file(file_id, file_path)
        print("[+] Ingestion complete.")
    except Exception as e:
        print(f"[!] Error during ingestion: {e}")
        return

    # 4. Create Source records from the ingested rows (Async)
    print("[*] Creating Source records from Excel data...")
    async with AsyncSessionLocal() as db:
        try:
            result = await create_sources_from_excel(db)
            print("[+] Source creation complete.")
            print(f"    - Created: {result.get('created', 0)}")
            print(f"    - Skipped: {result.get('skipped', 0)}")
            if "error" in result:
                print(f"    - Error: {result['error']}")
        except Exception as e:
            print(f"[!] Error during source creation: {e}")

if __name__ == "__main__":
    asyncio.run(run_import())
