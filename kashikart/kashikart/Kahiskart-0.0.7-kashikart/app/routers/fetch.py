from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select, func
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.fetch_log import FetchLog, FetchStatus
from app.models.source import Source
from app.models.user import User
from app.auth.dependencies import get_current_user, get_current_superuser
from app.schemas.fetch_log_schema import (
    FetchLogResponse, FetchLogList, FetchLogFilter
)
from app.scheduler.jobs import (
    fetch_all_sources_job,
    fetch_single_source_job,
    fetch_sources_by_keywords_job,
)

router = APIRouter()


class KeywordFetchRequest(BaseModel):
    keywords: List[str] = Field(..., min_items=1, description="Keywords to match (case-insensitive)")
    source_ids: Optional[List[int]] = Field(
        default=None,
        description="Limit fetch to these source IDs. If omitted, all active sources are used."
    )


@router.get("/logs", response_model=FetchLogList)
async def get_fetch_logs(
        status: Optional[str] = Query(None),
        source_id: Optional[int] = Query(None),
        search: Optional[str] = Query(None),
        page: int = Query(1, ge=1),
        page_size: int = Query(25, ge=1, le=100),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_superuser)
):
    # Base query
    base_query = select(FetchLog)

    # Apply filters
    if status:
        base_query = base_query.where(FetchLog.status == status)

    if source_id:
        base_query = base_query.where(FetchLog.source_id == source_id)

    # Search filter
    if search:
        term = f"%{search.strip()}%"
        base_query = base_query.join(
            Source,
            FetchLog.source_id == Source.id
        ).where(
            or_(
                FetchLog.message.ilike(term),
                Source.name.ilike(term)
            )
        )

    # ---------- COUNTS (without pagination) ----------
    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar() or 0

    # Status counts
    status_count_result = await db.execute(
        select(
            FetchLog.status,
            func.count(FetchLog.id)
        )
        .group_by(FetchLog.status)
    )
    status_counts = status_count_result.all()

    counts_map = {
        FetchStatus.SUCCESS: 0,
        FetchStatus.WARNING: 0,
        FetchStatus.ERROR: 0,
        FetchStatus.INFO: 0,
    }

    for status_key, count in status_counts:
        counts_map[status_key] = count

    # ---------- PAGINATION ----------
    offset = (page - 1) * page_size

    result = await db.execute(
        base_query
        .order_by(FetchLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    logs = result.scalars().all()

    return {
        "total": total,
        "success_count": counts_map[FetchStatus.SUCCESS],
        "warning_count": counts_map[FetchStatus.WARNING],
        "error_count": counts_map[FetchStatus.ERROR],
        "info_count": counts_map[FetchStatus.INFO],
        "items": logs
    }


@router.post("/now")
async def fetch_now(
        source_id: Optional[int] = None,
        background_tasks: BackgroundTasks = None,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if source_id:
        result = await db.execute(
            select(Source).where(Source.id == source_id)
        )
        source = result.scalar_one_or_none()

        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found"
            )

        if not source.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot fetch from disabled source"
            )

        # Trigger fetch in background
        background_tasks.add_task(fetch_single_source_job, source_id)

        return {
            "message": f"Fetch started for {source.name}",
            "source_id": source_id,
            "source_name": source.name
        }
    else:
        # Fetch all active sources
        background_tasks.add_task(fetch_all_sources_job)

        active_count_result = await db.execute(
            select(func.count(Source.id)).where(Source.is_active == True)
        )
        active_count = active_count_result.scalar() or 0

        return {
            "message": "Fetch started for all active sources",
            "active_sources": active_count
        }


@router.post("/by-keywords")
async def fetch_by_keywords(
        payload: KeywordFetchRequest,
        background_tasks: BackgroundTasks = None,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Trigger a background fetch that only keeps tenders matching the provided
    keywords. Optionally limit to a subset of source IDs.
    """
    keywords = [kw.strip() for kw in payload.keywords if kw and kw.strip()]
    if not keywords:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one non-empty keyword is required"
        )

    source_ids = payload.source_ids
    if source_ids:
        # Validate source IDs and ensure they are active
        result = await db.execute(
            select(Source.id).where(
                Source.is_active == True,
                Source.id.in_(source_ids)
            )
        )
        valid_ids = set(result.scalars().all())
        missing = set(source_ids) - valid_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or inactive source_ids: {sorted(missing)}"
            )
        source_ids = list(valid_ids)

    background_tasks.add_task(
        fetch_sources_by_keywords_job,
        keywords,
        source_ids
    )

    return {
        "message": "Keyword-based fetch started",
        "keywords": keywords,
        "source_filter": source_ids or "all active"
    }


@router.get("/status")
async def get_fetch_status(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # Get last successful fetch
    result = await db.execute(
        select(FetchLog)
        .where(FetchLog.status == FetchStatus.SUCCESS)
        .order_by(FetchLog.created_at.desc())
        .limit(1)
    )
    last_success = result.scalar_one_or_none()

    # Get sources that haven't been fetched in 24 hours
    day_ago = datetime.utcnow() - timedelta(hours=24)

    stale_result = await db.execute(
        select(func.count(Source.id))
        .where(
            Source.is_active == True,
            Source.last_fetch_at < day_ago
        )
    )
    stale_sources = stale_result.scalar() or 0

    return {
        "last_sync": last_success.created_at if last_success else None,
        "last_sync_message": last_success.message if last_success else "No successful fetch yet",
        "stale_sources": stale_sources,
        "is_fetching": False  # TODO: Track actual fetch status
    }


@router.delete("/logs/clear")
async def clear_old_logs(
        days: int = Query(30, ge=7, le=365),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_superuser)
):
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(FetchLog).where(FetchLog.created_at < cutoff_date)
    )
    logs_to_delete = result.scalars().all()

    for log in logs_to_delete:
        await db.delete(log)

    await db.commit()

    return {
        "message": f"Deleted {len(logs_to_delete)} log entries older than {days} days",
        "deleted_count": len(logs_to_delete)
    }
