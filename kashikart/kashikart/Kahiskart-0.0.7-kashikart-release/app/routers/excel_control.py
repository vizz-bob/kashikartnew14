# # from fastapi import APIRouter
# # from app.businessLogic.excel_processor_local import ExcelProcessorLocal

# # router = APIRouter(prefix="/excel", tags=["Excel"])

# # @router.post("/test-load")
# # async def test_excel_load():
# #     await ExcelProcessorLocal.process_excel_once()
# #     return {"status": "Excel loaded (test rows only)"}
# from fastapi import APIRouter
# from app.core.database import AsyncSessionLocal
# from sqlalchemy import select
# from datetime import datetime
# from app.models.excel_raw import ExcelFile

# router = APIRouter(prefix="/excel", tags=["Excel"])


# @router.post("/register-file")
# async def register_excel_file(path: str):
#     # Convert Windows path → Unix style
#     path = path.replace("\\", "/").strip('\'"')

#     async with AsyncSessionLocal() as db:

#         # Check existing
#         result = await db.execute(
#             select(ExcelFile).where(ExcelFile.file_path == path)
#         )
#         existing = result.scalar_one_or_none()

#         if existing:
#             return {"status": "already exists", "id": existing.id}

#         excel_file = ExcelFile(
#             file_path=path,
#             created_at=datetime.utcnow()
#         )
#         db.add(excel_file)
#         await db.commit()
#         await db.refresh(excel_file)

#     return {"status": "registered", "id": excel_file.id}

from fastapi import APIRouter, Query, Depends, BackgroundTasks
from app.core.database import AsyncSessionLocal, get_db
from sqlalchemy import select, func
from datetime import datetime
from app.models.excel_raw import ExcelFile, ExcelRowRaw
from app.models.source import Source
from app.models.tender import Tender
from app.businessLogic.excel_importer import import_excel_tenders
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

router = APIRouter(prefix="/excel", tags=["Excel"])


async def process_excel_file_background(file_id: int):
    """
    Background task to process Excel file after registration.
    This runs automatically after a file path is registered.
    """
    async with AsyncSessionLocal() as db:
        try:
            print(f"🔄 Starting background import for file ID: {file_id}")

            # Step 1: Import Excel rows to tenders table
            result = await import_excel_tenders(db)

            print(f"✅ Import completed: {result['imported']} tenders created")
            print(f"⏭️ Skipped: {result['skipped']} rows")

            # Step 2: Create sources from Excel data
            await create_sources_from_excel(db)

            print(f"✅ Background processing completed for file ID: {file_id}")

        except Exception as e:
            print(f"❌ Background import failed: {str(e)}")


async def create_sources_from_excel(db: AsyncSession):
    """
    Automatically create Source records from Excel data.
    Scans Excel rows for unique sources and creates them.
    """
    try:
        # Get all Excel rows
        result = await db.execute(select(ExcelRowRaw))
        rows = result.scalars().all()

        created_count = 0
        skipped_count = 0

        # Track unique sources
        seen_sources = set()

        for row in rows:
            data = row.row_data or {}

            # Extract source information
            source_name = (
                    data.get('Source') or
                    data.get('source') or
                    data.get('City/Agency')
            )

            source_url = (
                    data.get('Web Source Data Link (Links of Tender Release Sources)') or
                    data.get('Column3 (Source Link 1)') or
                    data.get('Column4')
            )

            # Skip invalid sources
            if not source_name or not source_url:
                continue

            # Skip headers
            if source_name in ['Florida State', 'Washington State', 'Oregon State']:
                continue

            # Skip duplicates
            source_key = f"{source_name}|{source_url}".lower()
            if source_key in seen_sources:
                skipped_count += 1
                continue

            seen_sources.add(source_key)

            # Check if source already exists
            existing = await db.execute(
                select(Source).where(Source.name == source_name)
            )

            if existing.scalar_one_or_none():
                skipped_count += 1
                continue

            # Determine login requirement
            login_required = (
                    data.get('User Login Required?') == 'Yes' or
                    data.get('User') not in [None, '', '-']
            )

            # Create new source
            new_source = Source(
                name=source_name[:255],
                url=source_url[:500],
                login_required=login_required,
                password=data.get('Password') if login_required else None,
                scraper_type='excel',
                status='ACTIVE',
                is_active=True,
                description=f"Auto-imported from Excel: {data.get('Remarks', '')}",
                created_at=datetime.utcnow(),
            )

            db.add(new_source)
            created_count += 1

        await db.commit()

        print(f"📊 Source creation completed:")
        print(f"  ✅ Created: {created_count} sources")
        print(f"  ⏭️ Skipped: {skipped_count} duplicates")

        return {
            "created": created_count,
            "skipped": skipped_count
        }

    except Exception as e:
        print(f"❌ Error creating sources: {str(e)}")
        await db.rollback()
        return {
            "created": 0,
            "skipped": 0,
            "error": str(e)
        }

@router.post("/import-to-tenders")
async def import_excel_to_tenders(
        db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger import of Excel data to tenders table.
    Also creates sources from Excel data.
    """
    try:
        # Import tenders
        tender_result = await import_excel_tenders(db)

        # Create sources
        source_result = await create_sources_from_excel(db)

        return {
            "status": "success",
            "tenders": tender_result,
            "sources": source_result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/import-status")
async def get_import_status(db: AsyncSession = Depends(get_db)):
    """
    Get status of Excel data import.
    Shows counts of Excel rows, tenders, and sources.
    """
    try:
        # Count Excel rows
        excel_count = await db.scalar(
            select(func.count()).select_from(ExcelRowRaw)
        )

        # Count imported tenders
        tender_count = await db.scalar(
            select(func.count()).select_from(Tender).where(
                Tender.imported_from_excel == True
            )
        )

        # Count sources
        source_count = await db.scalar(
            select(func.count()).select_from(Source).where(
                Source.scraper_type == 'excel'
            )
        )

        return {
            "excel_rows": excel_count,
            "imported_tenders": tender_count,
            "excel_sources": source_count,
            "import_rate": f"{(tender_count / excel_count * 100):.1f}%" if excel_count > 0 else "0%"
        }

    except Exception as e:
        return {
            "error": str(e)
        }


# Register Excel File Path
@router.post("/register-file")
async def register_excel_file(
        path: str,
        background_tasks: BackgroundTasks,
        auto_import: bool = Query(True, description="Automatically import data after registration")
):
    """
    Register Excel file path and optionally trigger automatic import.

    Parameters:
    - path: File path to the Excel file
    - auto_import: If True, automatically imports data to tenders and creates sources

    Returns:
    - status: Registration status
    - id: File ID
    - auto_import_triggered: Whether background import was started
    """
    path = path.replace("\\", "/").strip('\'"')

    async with AsyncSessionLocal() as db:
        # Check existing
        result = await db.execute(
            select(ExcelFile).where(ExcelFile.file_path == path)
        )
        existing = result.scalar_one_or_none()

        if existing:
            return {
                "status": "already exists",
                "id": existing.id,
                "auto_import_triggered": False
            }

        # Create new file record
        excel_file = ExcelFile(
            file_path=path,
            created_at=datetime.utcnow()
        )
        db.add(excel_file)
        await db.commit()
        await db.refresh(excel_file)

        # Trigger background import if enabled
        if auto_import:
            background_tasks.add_task(
                process_excel_file_background,
                excel_file.id
            )

            return {
                "status": "registered",
                "id": excel_file.id,
                "auto_import_triggered": True,
                "message": "File registered. Import started in background."
            }

        return {
            "status": "registered",
            "id": excel_file.id,
            "auto_import_triggered": False
        }


# GET ALL REGISTERED FILES
@router.get("/files")
async def get_all_excel_files():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ExcelFile))
        files = result.scalars().all()

        return [
            {
                "id": f.id,
                "file_path": f.file_path,
                "created_at": f.created_at
            }
            for f in files
        ]



# GET FILE BY ID
@router.get("/file/{file_id}")
async def get_excel_file(file_id: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ExcelFile).where(ExcelFile.id == file_id))
        file = result.scalar_one_or_none()

        if not file:
            return {"error": "File not found"}

        return {
            "id": file.id,
            "file_path": file.file_path,
            "created_at": file.created_at
        }



# PAGINATION (Enterprise Style)
@router.get("/files/paginated")
async def get_files_paginated(
    limit: int = Query(10, le=100),
    offset: int = Query(0)
):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ExcelFile).limit(limit).offset(offset))
        files = result.scalars().all()

        return {
            "count": len(files),
            "data": [
                {"id": f.id, "file_path": f.file_path, "created_at": f.created_at}
                for f in files
            ]
        }

# @router.get("/all")
# async def get_all_rows():
#     async with AsyncSessionLocal() as db:
#         result = await db.execute(select(ExcelRowRaw))
#         rows = result.scalars().all()

#         return [
#             {
#                 "id": r.id,
#                 "sheet_id": r.sheet_id,
#                 "row_index": r.row_index,
#                 "row_data": r.row_data,
#                 "created_at": r.created_at
#             }
#             for r in rows
#         ]

@router.get("/all")
async def get_all_rows_paginated(
    page: int = Query(1, ge=1),
    limit: int = Query(100, le=1000)
):
    offset = (page - 1) * limit

    async with AsyncSessionLocal() as db:

        # Get total rows count
        total_result = await db.execute(select(func.count()).select_from(ExcelRowRaw))
        total_rows = total_result.scalar()

        # Fetch paginated rows
        result = await db.execute(
            select(ExcelRowRaw)
            .order_by(ExcelRowRaw.id)
            .limit(limit)
            .offset(offset)
        )
        rows = result.scalars().all()

        return {
            "page": page,
            "limit": limit,
            "total_rows": total_rows,
            "total_pages": (total_rows // limit) + (1 if total_rows % limit else 0),
            "data": [
                {
                    "id": r.id,
                    "sheet_id": r.sheet_id,
                    "row_index": r.row_index,
                    "row_data": r.row_data,
                    "created_at": r.created_at
                }
                for r in rows
            ]
        }


@router.get("/sheet/{sheet_id}")
async def get_rows_by_sheet(sheet_id: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ExcelRowRaw).where(ExcelRowRaw.sheet_id == sheet_id)
        )
        rows = result.scalars().all()

        return rows

@router.get("/paginated")
async def get_rows_paginated(
    sheet_id: int,
    limit: int = Query(50, le=500),
    offset: int = 0
):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ExcelRowRaw)
            .where(ExcelRowRaw.sheet_id == sheet_id)
            .limit(limit)
            .offset(offset)
        )
        rows = result.scalars().all()

        return {
            "sheet_id": sheet_id,
            "limit": limit,
            "offset": offset,
            "count": len(rows),
            "data": [
                {
                    "id": r.id,
                    "row_index": r.row_index,
                    "row_data": r.row_data
                }
                for r in rows
            ]
        }
