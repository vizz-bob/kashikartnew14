from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.core.database import get_db
from app.models.onedrive import ExcelFileTracker, RawExcelSheet, SheetHeaderMapping, FileStatus

router = APIRouter(prefix="/powerbi", tags=["Power BI"])
logger = logging.getLogger(__name__)

# ============================================================================
# POWER BI DATA ENDPOINTS
# ============================================================================

@router.get("/data")
async def get_powerbi_data(
    source_website: Optional[str] = Query(None, description="Filter by source website"),
    sheet_name: Optional[str] = Query(None, description="Filter by sheet name"),
    date_from: Optional[str] = Query(None, description="Start date (ISO format: YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (ISO format: YYYY-MM-DD)"),
    tender_status: Optional[str] = Query(None, description="Filter by tender status"),
    include_raw_data: bool = Query(True, description="Include full raw JSON data"),
    limit: int = Query(10000, ge=1, le=50000, description="Maximum records to return"),
    db: Session = Depends(get_db)
):
    """
    Main Power BI data endpoint - Returns formatted tender data
    
    This endpoint is optimized for Power BI's Web connector:
    - Direct JSON output
    - Flattened structure
    - Pre-normalized fields
    - Metadata included
    
    Example Power BI M Query:
    ```
    let
        Source = Json.Document(Web.Contents("http://localhost:8000/api/v1/powerbi/data")),
        data = Source[data],
        ToTable = Table.FromList(data, Splitter.SplitByNothing()),
        ExpandedData = Table.ExpandRecordColumn(ToTable, "Column1", 
            {"tender_id", "title", "organization", "deadline", "value", "source"})
    in
        ExpandedData
    ```
    """
    try:
        # Build query
        query = db.query(RawExcelSheet).join(
            ExcelFileTracker,
            RawExcelSheet.file_id == ExcelFileTracker.file_id
        ).filter(
            ExcelFileTracker.status == FileStatus.DONE
        )
        
        # Apply filters
        if source_website:
            query = query.filter(RawExcelSheet.source_website == source_website)
        
        if sheet_name:
            query = query.filter(RawExcelSheet.sheet_name == sheet_name)
        
        if date_from:
            try:
                date_from_dt = datetime.fromisoformat(date_from)
                query = query.filter(RawExcelSheet.created_at >= date_from_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")
        
        if date_to:
            try:
                date_to_dt = datetime.fromisoformat(date_to)
                # Include the entire end date
                date_to_dt = date_to_dt + timedelta(days=1)
                query = query.filter(RawExcelSheet.created_at < date_to_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")
        
        # Order by most recent first
        query = query.order_by(RawExcelSheet.created_at.desc())
        
        # Get results with limit
        results = query.limit(limit).all()
        
        # Format data for Power BI
        formatted_data = []
        sources_set = set()
        sheets_set = set()
        
        for row in results:
            # Extract normalized fields
            row_data = {
                # Core identifiers
                "id": row.raw_id,
                "tender_id": row.tender_id or row.row_json.get('normalized_tender_id', ''),
                "row_number": row.row_number,
                
                # Normalized tender fields
                "title": row.row_json.get('normalized_title', ''),
                "organization": row.row_json.get('normalized_organization', ''),
                "deadline": row.row_json.get('normalized_deadline', ''),
                "publish_date": row.row_json.get('normalized_publish_date', ''),
                "value": row.row_json.get('normalized_value', ''),
                "status": row.row_json.get('normalized_status', tender_status or ''),
                "category": row.row_json.get('normalized_category', ''),
                "location": row.row_json.get('normalized_location', ''),
                
                # Source information
                "source_website": row.source_website or 'Unknown',
                "sheet_name": row.sheet_name,
                
                # Timestamps
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "created_date": row.created_at.date().isoformat() if row.created_at else None,
                "created_time": row.created_at.time().isoformat() if row.created_at else None,
            }
            
            # Include all raw data if requested
            if include_raw_data:
                # Merge raw JSON data (excluding normalized fields to avoid duplication)
                for key, value in row.row_json.items():
                    if not key.startswith('normalized_') and key not in row_data:
                        row_data[key] = value
            
            formatted_data.append(row_data)
            
            # Track unique values for metadata
            if row.source_website:
                sources_set.add(row.source_website)
            sheets_set.add(row.sheet_name)
        
        # Get latest file info
        latest_file = db.query(ExcelFileTracker).filter(
            ExcelFileTracker.status == FileStatus.DONE
        ).order_by(ExcelFileTracker.uploaded_at.desc()).first()
        
        # Calculate date range
        date_range = {}
        if results:
            dates = [r.created_at for r in results if r.created_at]
            if dates:
                date_range = {
                    "from": min(dates).isoformat(),
                    "to": max(dates).isoformat()
                }
        
        # Build response
        response = {
            "data": formatted_data,
            "metadata": {
                "total_records": len(formatted_data),
                "sources": sorted(list(sources_set)),
                "sheets": sorted(list(sheets_set)),
                "date_range": date_range,
                "last_updated": latest_file.uploaded_at.isoformat() if latest_file else None,
                "last_processed": latest_file.processed_at.isoformat() if latest_file and latest_file.processed_at else None,
                "filters_applied": {
                    "source_website": source_website,
                    "sheet_name": sheet_name,
                    "date_from": date_from,
                    "date_to": date_to,
                    "tender_status": tender_status
                }
            },
            "query_info": {
                "limit": limit,
                "returned": len(formatted_data),
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error in get_powerbi_data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/flat")
async def get_powerbi_data_flat(
    source_website: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(10000, ge=1, le=50000),
    db: Session = Depends(get_db)
):
    """
    Flattened Power BI data endpoint - Returns only normalized fields
    
    This endpoint returns a simpler structure without nested JSON,
    making it easier to import directly into Power BI.
    
    Use this when you only need the normalized tender fields.
    """
    try:
        query = db.query(RawExcelSheet).join(
            ExcelFileTracker,
            RawExcelSheet.file_id == ExcelFileTracker.file_id
        ).filter(
            ExcelFileTracker.status == FileStatus.DONE
        )
        
        if source_website:
            query = query.filter(RawExcelSheet.source_website == source_website)
        
        if date_from:
            date_from_dt = datetime.fromisoformat(date_from)
            query = query.filter(RawExcelSheet.created_at >= date_from_dt)
        
        if date_to:
            date_to_dt = datetime.fromisoformat(date_to) + timedelta(days=1)
            query = query.filter(RawExcelSheet.created_at < date_to_dt)
        
        results = query.order_by(RawExcelSheet.created_at.desc()).limit(limit).all()
        
        # Return flat list of records
        data = []
        for row in results:
            data.append({
                "id": row.raw_id,
                "tender_id": row.tender_id or row.row_json.get('normalized_tender_id', ''),
                "title": row.row_json.get('normalized_title', ''),
                "organization": row.row_json.get('normalized_organization', ''),
                "deadline": row.row_json.get('normalized_deadline', ''),
                "publish_date": row.row_json.get('normalized_publish_date', ''),
                "value": row.row_json.get('normalized_value', ''),
                "status": row.row_json.get('normalized_status', ''),
                "category": row.row_json.get('normalized_category', ''),
                "location": row.row_json.get('normalized_location', ''),
                "source": row.source_website or 'Unknown',
                "sheet": row.sheet_name,
                "date": row.created_at.isoformat() if row.created_at else None
            })
        
        return data
        
    except Exception as e:
        logger.error(f"Error in get_powerbi_data_flat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/by-source")
async def get_powerbi_data_by_source(
    limit_per_source: int = Query(1000, ge=1, le=10000),
    date_from: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get Power BI data grouped by source
    
    Returns data organized by source website with balanced representation
    from each source.
    """
    try:
        # Get all unique sources
        sources = db.query(RawExcelSheet.source_website).filter(
            RawExcelSheet.source_website.isnot(None)
        ).distinct().all()
        
        all_data = []
        
        for (source,) in sources:
            query = db.query(RawExcelSheet).join(
                ExcelFileTracker,
                RawExcelSheet.file_id == ExcelFileTracker.file_id
            ).filter(
                and_(
                    ExcelFileTracker.status == FileStatus.DONE,
                    RawExcelSheet.source_website == source
                )
            )
            
            if date_from:
                date_from_dt = datetime.fromisoformat(date_from)
                query = query.filter(RawExcelSheet.created_at >= date_from_dt)
            
            results = query.order_by(
                RawExcelSheet.created_at.desc()
            ).limit(limit_per_source).all()
            
            for row in results:
                all_data.append({
                    "id": row.raw_id,
                    "tender_id": row.tender_id or row.row_json.get('normalized_tender_id', ''),
                    "title": row.row_json.get('normalized_title', ''),
                    "organization": row.row_json.get('normalized_organization', ''),
                    "deadline": row.row_json.get('normalized_deadline', ''),
                    "value": row.row_json.get('normalized_value', ''),
                    "source": source,
                    "sheet": row.sheet_name,
                    "date": row.created_at.isoformat() if row.created_at else None
                })
        
        return {
            "data": all_data,
            "sources": len(sources),
            "total_records": len(all_data)
        }
        
    except Exception as e:
        logger.error(f"Error in get_powerbi_data_by_source: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AGGREGATION ENDPOINTS FOR POWER BI DASHBOARDS
# ============================================================================

@router.get("/statistics/overview")
async def get_statistics_overview(db: Session = Depends(get_db)):
    """
    Get comprehensive statistics for Power BI dashboards
    
    Returns aggregated data perfect for creating Power BI cards and KPIs
    """
    try:
        # Total tenders
        total_tenders = db.query(func.count(RawExcelSheet.raw_id)).scalar() or 0
        
        # Total sources
        total_sources = db.query(
            func.count(func.distinct(RawExcelSheet.source_website))
        ).filter(RawExcelSheet.source_website.isnot(None)).scalar() or 0
        
        # Total sheets
        total_sheets = db.query(
            func.count(func.distinct(RawExcelSheet.sheet_name))
        ).scalar() or 0
        
        # Tenders by source
        tenders_by_source = db.query(
            RawExcelSheet.source_website,
            func.count(RawExcelSheet.raw_id).label('count')
        ).filter(
            RawExcelSheet.source_website.isnot(None)
        ).group_by(
            RawExcelSheet.source_website
        ).all()
        
        # Recent activity (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_tenders = db.query(
            func.count(RawExcelSheet.raw_id)
        ).filter(
            RawExcelSheet.created_at >= seven_days_ago
        ).scalar() or 0
        
        # Tenders by date (last 30 days for trend analysis)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        tenders_by_date = db.query(
            func.date(RawExcelSheet.created_at).label('date'),
            func.count(RawExcelSheet.raw_id).label('count')
        ).filter(
            RawExcelSheet.created_at >= thirty_days_ago
        ).group_by(
            func.date(RawExcelSheet.created_at)
        ).order_by('date').all()
        
        # Latest update
        latest_file = db.query(ExcelFileTracker).filter(
            ExcelFileTracker.status == FileStatus.DONE
        ).order_by(ExcelFileTracker.uploaded_at.desc()).first()
        
        return {
            "overview": {
                "total_tenders": total_tenders,
                "total_sources": total_sources,
                "total_sheets": total_sheets,
                "recent_tenders_7d": recent_tenders,
                "last_updated": latest_file.uploaded_at.isoformat() if latest_file else None
            },
            "by_source": [
                {"source": source or "Unknown", "count": count}
                for source, count in tenders_by_source
            ],
            "trend_30d": [
                {"date": date.isoformat(), "count": count}
                for date, count in tenders_by_date
            ]
        }
        
    except Exception as e:
        logger.error(f"Error in get_statistics_overview: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/by-category")
async def get_statistics_by_category(db: Session = Depends(get_db)):
    """
    Get tender statistics grouped by category
    
    Useful for Power BI pie charts and category analysis
    """
    try:
        # Get categories from normalized data
        results = db.query(RawExcelSheet).all()
        
        category_counts = {}
        for row in results:
            category = row.row_json.get('normalized_category', 'Uncategorized')
            if category:
                category_counts[category] = category_counts.get(category, 0) + 1
        
        data = [
            {"category": cat, "count": count}
            for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        return {
            "data": data,
            "total_categories": len(data),
            "total_tenders": sum(item["count"] for item in data)
        }
        
    except Exception as e:
        logger.error(f"Error in get_statistics_by_category: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/by-location")
async def get_statistics_by_location(db: Session = Depends(get_db)):
    """
    Get tender statistics grouped by location
    
    Perfect for Power BI map visualizations
    """
    try:
        results = db.query(RawExcelSheet).all()
        
        location_counts = {}
        for row in results:
            location = row.row_json.get('normalized_location', 'Unknown')
            if location:
                location_counts[location] = location_counts.get(location, 0) + 1
        
        data = [
            {"location": loc, "count": count}
            for loc, count in sorted(location_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        return {
            "data": data,
            "total_locations": len(data),
            "total_tenders": sum(item["count"] for item in data)
        }
        
    except Exception as e:
        logger.error(f"Error in get_statistics_by_location: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/value-analysis")
async def get_value_analysis(db: Session = Depends(get_db)):
    """
    Analyze tender values for Power BI financial dashboards
    
    Returns value distributions, ranges, and totals
    """
    try:
        results = db.query(RawExcelSheet).all()
        
        values = []
        for row in results:
            value_str = row.row_json.get('normalized_value', '')
            if value_str:
                # Try to extract numeric value
                try:
                    # Remove currency symbols and commas
                    clean_value = ''.join(c for c in str(value_str) if c.isdigit() or c == '.')
                    if clean_value:
                        values.append(float(clean_value))
                except:
                    continue
        
        if not values:
            return {
                "total_value": 0,
                "average_value": 0,
                "median_value": 0,
                "max_value": 0,
                "min_value": 0,
                "tenders_with_value": 0
            }
        
        values.sort()
        
        return {
            "total_value": sum(values),
            "average_value": sum(values) / len(values),
            "median_value": values[len(values) // 2],
            "max_value": max(values),
            "min_value": min(values),
            "tenders_with_value": len(values),
            "value_ranges": {
                "under_100k": len([v for v in values if v < 100000]),
                "100k_to_1m": len([v for v in values if 100000 <= v < 1000000]),
                "1m_to_10m": len([v for v in values if 1000000 <= v < 10000000]),
                "over_10m": len([v for v in values if v >= 10000000])
            }
        }
        
    except Exception as e:
        logger.error(f"Error in get_value_analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# METADATA ENDPOINTS
# ============================================================================

@router.get("/sources")
async def list_sources(db: Session = Depends(get_db)):
    """
    List all unique tender sources
    
    Use this in Power BI slicers for filtering
    """
    try:
        sources = db.query(
            RawExcelSheet.source_website,
            func.count(RawExcelSheet.raw_id).label('count')
        ).filter(
            RawExcelSheet.source_website.isnot(None)
        ).group_by(
            RawExcelSheet.source_website
        ).all()
        
        return [
            {"source": source, "tender_count": count}
            for source, count in sources
        ]
        
    except Exception as e:
        logger.error(f"Error in list_sources: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sheets")
async def list_sheets(
    source_website: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all sheet names with optional source filter
    """
    try:
        query = db.query(
            RawExcelSheet.sheet_name,
            RawExcelSheet.source_website,
            func.count(RawExcelSheet.raw_id).label('count')
        )
        
        if source_website:
            query = query.filter(RawExcelSheet.source_website == source_website)
        
        sheets = query.group_by(
            RawExcelSheet.sheet_name,
            RawExcelSheet.source_website
        ).all()
        
        return [
            {
                "sheet_name": sheet,
                "source": source or "Unknown",
                "tender_count": count
            }
            for sheet, source, count in sheets
        ]
        
    except Exception as e:
        logger.error(f"Error in list_sheets: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/refresh-info")
async def get_refresh_info(db: Session = Depends(get_db)):
    """
    Get information about data refresh status
    
    Useful for showing last refresh time in Power BI dashboards
    """
    try:
        latest_file = db.query(ExcelFileTracker).order_by(
            ExcelFileTracker.uploaded_at.desc()
        ).first()
        
        if not latest_file:
            return {
                "last_refresh": None,
                "status": "No data",
                "total_files": 0
            }
        
        total_files = db.query(func.count(ExcelFileTracker.file_id)).scalar()
        
        return {
            "last_refresh": latest_file.uploaded_at.isoformat(),
            "last_processed": latest_file.processed_at.isoformat() if latest_file.processed_at else None,
            "status": latest_file.status.value,
            "total_files": total_files,
            "latest_file_sheets": latest_file.sheet_count,
            "latest_file_rows": latest_file.total_rows
        }
        
    except Exception as e:
        logger.error(f"Error in get_refresh_info: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))