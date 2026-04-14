from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, and_, desc
from typing import Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.fetch_log import FetchLog, FetchStatus
from app.models.tender import Tender
from app.models.source import Source
from app.models.keyword import Keyword, TenderKeywordMatch
from app.auth.dependencies import get_current_superuser

router = APIRouter(tags=["System Logs"])


@router.get("/")
async def get_system_logs(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_superuser)
):
    """Return system logs (fetch_logs) for the System Logs page."""

    stmt = select(FetchLog)

    # Search filter
    if search:
        stmt = stmt.where(
            FetchLog.source_name.ilike(f"%{search}%") |
            FetchLog.message.ilike(f"%{search}%")
        )

    # Status filter
    if status and status != "All Status":
        status_map = {
            "Success": FetchStatus.SUCCESS,
            "Warning": FetchStatus.WARNING,
            "Error": FetchStatus.ERROR,
            "Info": FetchStatus.INFO,
        }
        if status in status_map:
            stmt = stmt.where(FetchLog.status == status_map[status])

    # Date filter
    if date:
        try:
            filter_date = datetime.strptime(date, "%Y-%m-%d")
            next_day = filter_date + timedelta(days=1)
            stmt = stmt.where(
                and_(
                    FetchLog.created_at >= filter_date,
                    FetchLog.created_at < next_day
                )
            )
        except ValueError:
            pass

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Stats
    all_logs_stmt = select(FetchLog)
    stats_result = await db.execute(all_logs_stmt)
    all_logs = stats_result.scalars().all()

    stats = {
        "Success": sum(1 for l in all_logs if l.status == FetchStatus.SUCCESS),
        "Warning": sum(1 for l in all_logs if l.status == FetchStatus.WARNING),
        "Error": sum(1 for l in all_logs if l.status in (FetchStatus.ERROR, FetchStatus.FAILED)),
        "Info": sum(1 for l in all_logs if l.status == FetchStatus.INFO),
    }

    # Paginated results
    offset = (page - 1) * size
    stmt = stmt.order_by(FetchLog.created_at.desc()).offset(offset).limit(size)

    result = await db.execute(stmt)
    logs = result.scalars().all()

    status_display_map = {
        FetchStatus.SUCCESS: "Success",
        FetchStatus.WARNING: "Warning",
        FetchStatus.ERROR: "Error",
        FetchStatus.FAILED: "Error",
        FetchStatus.RUNNING: "Info",
        FetchStatus.INFO: "Info",
    }

    items = []
    for log in logs:
        created = log.created_at or log.started_at or datetime.utcnow()
        items.append({
            "id": log.id,
            "date": created.strftime("%Y-%m-%d"),
            "time": created.strftime("%H:%M:%S"),
            "source": log.source_name or f"Source #{log.source_id}",
            "status": status_display_map.get(log.status, "Info"),
            "message": log.message or "No details",
            "tenders_found": log.tenders_found or 0,
            "new_tenders": log.new_tenders or 0,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "stats": stats
    }


@router.delete("/")
async def clear_system_logs(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_superuser)
):
    """Clear all system logs."""
    await db.execute(
        FetchLog.__table__.delete()
    )
    await db.commit()
    return {"message": "All logs cleared"}
