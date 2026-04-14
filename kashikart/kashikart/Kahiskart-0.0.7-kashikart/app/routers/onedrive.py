from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.core.database import get_db
from app.core.config import settings
from app.businessLogic.excel_processor import ExcelProcessor
from app.schemas.onedrive_schema import (
    ProcessFileRequest, ProcessFileResponse, GetDataRequest, GetDataResponse,
    FileTrackerResponse, SheetListResponse, HeaderMappingResponse,
    TenderDataResponse, PowerBIDataResponse, StatisticsResponse
)
from app.models.onedrive import ExcelFileTracker, RawExcelSheet, SheetHeaderMapping, FileStatus

router = APIRouter(prefix="/onedrive", tags=["OneDrive"])
logger = logging.getLogger(__name__)

@router.post("/process", response_model=ProcessFileResponse)
async def process_onedrive_file(
    request: ProcessFileRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Download and process Excel file from OneDrive
    
    - **share_link**: OneDrive share link (optional, uses default from config)
    - **force_refresh**: Force reprocessing even if file hasn't changed
    """
    try:
        share_link = request.share_link or settings.ONEDRIVE_SHARE_LINK
        
        if not share_link:
            raise HTTPException(
                status_code=400,
                detail="No OneDrive share link provided"
            )
        
        processor = ExcelProcessor(db)
        
        # Process in background for large files
        if request.force_refresh:
            background_tasks.add_task(
                processor.process_onedrive_file,
                share_link,
                request.force_refresh
            )
            return ProcessFileResponse(
                success=True,
                message="File processing started in background",
                file_tracker=None
            )
        
        # Process synchronously
        file_tracker = processor.process_onedrive_file(share_link, request.force_refresh)
        
        if not file_tracker:
            raise HTTPException(
                status_code=500,
                detail="Failed to process OneDrive file"
            )
        
        return ProcessFileResponse(
            success=True,
            message=f"Successfully processed {file_tracker.total_rows} rows from {file_tracker.sheet_count} sheets",
            file_tracker=FileTrackerResponse.model_validate(file_tracker)
        )
        
    except Exception as e:
        logger.error(f"Error in process_onedrive_file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files", response_model=List[FileTrackerResponse])
async def list_files(
    status: Optional[str] = None,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    List all processed files with optional status filter
    """
    query = db.query(ExcelFileTracker).order_by(ExcelFileTracker.uploaded_at.desc())
    
    if status:
        try:
            status_enum = FileStatus(status.upper())
            query = query.filter(ExcelFileTracker.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    files = query.offset(offset).limit(limit).all()
    return [FileTrackerResponse.model_validate(f) for f in files]

@router.get("/files/{file_id}", response_model=FileTrackerResponse)
async def get_file_info(
    file_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific file"""
    file = db.query(ExcelFileTracker).filter(ExcelFileTracker.file_id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileTrackerResponse.model_validate(file)

@router.get("/files/{file_id}/sheets", response_model=SheetListResponse)
async def list_sheets(
    file_id: int,
    db: Session = Depends(get_db)
):
    """Get list of all sheets in a file"""
    file = db.query(ExcelFileTracker).filter(ExcelFileTracker.file_id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Get unique sheet names
    sheets = db.query(RawExcelSheet.sheet_name).filter(
        RawExcelSheet.file_id == file_id
    ).distinct().all()
    
    return SheetListResponse(
        file_id=file_id,
        sheets=[s[0] for s in sheets]
    )

@router.post("/data", response_model=GetDataResponse)
async def get_sheet_data(
    request: GetDataRequest,
    db: Session = Depends(get_db)
):
    """
    Get sheet data with optional filtering
    
    - **file_id**: Filter by file ID (optional)
    - **sheet_name**: Filter by sheet name (optional)
    - **limit**: Number of records to return
    - **offset**: Number of records to skip
    """
    processor = ExcelProcessor(db)
    
    # Get data
    data = processor.get_sheet_data(
        file_id=request.file_id,
        sheet_name=request.sheet_name,
        limit=request.limit,
        offset=request.offset
    )
    
    # Get total count
    query = db.query(RawExcelSheet)
    if request.file_id:
        query = query.filter(RawExcelSheet.file_id == request.file_id)
    if request.sheet_name:
        query = query.filter(RawExcelSheet.sheet_name == request.sheet_name)
    
    total_count = query.count()
    
    # Get file info if file_id provided
    file_info = None
    if request.file_id:
        file = db.query(ExcelFileTracker).filter(
            ExcelFileTracker.file_id == request.file_id
        ).first()
        if file:
            file_info = FileTrackerResponse.model_validate(file)
    
    return GetDataResponse(
        total_count=total_count,
        data=[SheetDataResponse.model_validate(d) for d in data],
        file_info=file_info
    )

@router.get("/sheets/{sheet_name}/mapping", response_model=HeaderMappingResponse)
async def get_sheet_mapping(
    sheet_name: str,
    db: Session = Depends(get_db)
):
    """Get header mapping for a specific sheet"""
    mapping = db.query(SheetHeaderMapping).filter(
        SheetHeaderMapping.sheet_name == sheet_name
    ).first()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Sheet mapping not found")
    
    return HeaderMappingResponse.model_validate(mapping)

@router.get("/tenders", response_model=List[TenderDataResponse])
async def get_normalized_tenders(
    source_website: Optional[str] = None,
    sheet_name: Optional[str] = None,
    tender_id: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get normalized tender data across all sheets
    
    - **source_website**: Filter by source website
    - **sheet_name**: Filter by sheet name
    - **tender_id**: Filter by tender ID
    - **limit**: Number of records
    - **offset**: Skip records
    """
    query = db.query(RawExcelSheet)
    
    if source_website:
        query = query.filter(RawExcelSheet.source_website == source_website)
    
    if sheet_name:
        query = query.filter(RawExcelSheet.sheet_name == sheet_name)
    
    if tender_id:
        query = query.filter(RawExcelSheet.tender_id == tender_id)
    
    query = query.order_by(RawExcelSheet.created_at.desc())
    results = query.offset(offset).limit(limit).all()
    
    # Transform to normalized format
    tenders = []
    for row in results:
        tender = TenderDataResponse(
            tender_id=row.row_json.get('normalized_tender_id'),
            title=row.row_json.get('normalized_title'),
            organization=row.row_json.get('normalized_organization'),
            deadline=row.row_json.get('normalized_deadline'),
            publish_date=row.row_json.get('normalized_publish_date'),
            value=row.row_json.get('normalized_value'),
            status=row.row_json.get('normalized_status'),
            category=row.row_json.get('normalized_category'),
            location=row.row_json.get('normalized_location'),
            source_website=row.source_website,
            sheet_name=row.sheet_name,
            raw_data=row.row_json,
            created_at=row.created_at
        )
        tenders.append(tender)
    
    return tenders

@router.get("/powerbi/data", response_model=PowerBIDataResponse)
async def get_powerbi_data(
    source_website: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get data formatted for Power BI consumption
    
    - **source_website**: Filter by source
    - **date_from**: Filter from date (ISO format)
    - **date_to**: Filter to date (ISO format)
    """
    from datetime import datetime
    
    query = db.query(RawExcelSheet)
    
    if source_website:
        query = query.filter(RawExcelSheet.source_website == source_website)
    
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from)
            query = query.filter(RawExcelSheet.created_at >= date_from_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format")
    
    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to)
            query = query.filter(RawExcelSheet.created_at <= date_to_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format")
    
    results = query.all()
    
    # Format for Power BI
    data = []
    for row in results:
        record = {
            'id': row.raw_id,
            'tender_id': row.tender_id or row.row_json.get('normalized_tender_id'),
            'source': row.source_website,
            'sheet': row.sheet_name,
            'created_at': row.created_at.isoformat(),
            **row.row_json  # Include all original fields
        }
        data.append(record)
    
    latest_file = db.query(ExcelFileTracker).order_by(
        ExcelFileTracker.uploaded_at.desc()
    ).first()
    
    return PowerBIDataResponse(
        data=data,
        metadata={
            'source_websites': list(set([r.source_website for r in results if r.source_website])),
            'sheets': list(set([r.sheet_name for r in results])),
            'date_range': {
                'from': min([r.created_at for r in results]).isoformat() if results else None,
                'to': max([r.created_at for r in results]).isoformat() if results else None
            }
        },
        last_updated=latest_file.uploaded_at if latest_file else datetime.utcnow(),
        total_records=len(data)
    )

@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(db: Session = Depends(get_db)):
    """Get overall statistics about processed data"""
    from sqlalchemy import func
    
    # Total files
    total_files = db.query(func.count(ExcelFileTracker.file_id)).scalar()
    
    # Files by status
    status_counts = db.query(
        ExcelFileTracker.status,
        func.count(ExcelFileTracker.file_id)
    ).group_by(ExcelFileTracker.status).all()
    
    files_by_status = {status.value: count for status, count in status_counts}
    
    # Total rows
    total_rows = db.query(func.count(RawExcelSheet.raw_id)).scalar()
    
    # Total unique sheets
    total_sheets = db.query(func.count(func.distinct(RawExcelSheet.sheet_name))).scalar()
    
    # Rows by source
    source_counts = db.query(
        RawExcelSheet.source_website,
        func.count(RawExcelSheet.raw_id)
    ).group_by(RawExcelSheet.source_website).all()
    
    rows_by_source = {source or 'Unknown': count for source, count in source_counts}
    
    # Latest update
    latest_file = db.query(ExcelFileTracker).order_by(
        ExcelFileTracker.uploaded_at.desc()
    ).first()
    
    return StatisticsResponse(
        total_files=total_files,
        total_sheets=total_sheets,
        total_rows=total_rows,
        files_by_status=files_by_status,
        rows_by_source=rows_by_source,
        latest_update=latest_file.uploaded_at if latest_file else None
    )

@router.delete("/files/{file_id}")
async def delete_file(
    file_id: int,
    db: Session = Depends(get_db)
):
    """Delete a file and all its associated data"""
    file = db.query(ExcelFileTracker).filter(ExcelFileTracker.file_id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    db.delete(file)
    db.commit()
    
    return {"message": f"File {file_id} deleted successfully"}