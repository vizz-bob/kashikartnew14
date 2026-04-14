from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, and_, desc, select
from sqlalchemy.orm import joinedload
import asyncio
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.models.tender import Tender
from app.models.source import Source
from app.models.keyword import Keyword, TenderKeywordMatch
from app.models.notification import Notification
from app.auth.dependencies import get_current_user


from app.businessLogic.fetch_service import FetchService
from app.models.fetch_log import FetchLog, FetchStatus


router = APIRouter(tags=["Dashboard"])


def to_ist(utc_dt: datetime) -> str:
    """
    Helper to convert UTC datetime to IST string for display.
    Kashikart backend stores all timestamps in UTC in the DB.
    IST offset is UTC + 5:30.
    """
    if not utc_dt:
        return "Never"
    # IST = UTC + 5:30
    ist_dt = utc_dt + timedelta(hours=5, minutes=30)
    return ist_dt.strftime("%Y-%m-%d %I:%M:%S %p")


# ===========================
# SYNC NOW
# ===========================
# Semaphore to limit total concurrent scrapers system-wide
scraper_semaphore = asyncio.Semaphore(5)

def run_sync_task(source_ids):
    """Background task to sync sources with concurrency control"""
    async def inner():
        for sid in source_ids:
            async with scraper_semaphore:
                from app.core.database import AsyncSessionLocal
                async with AsyncSessionLocal() as local_db:
                    local_fetch_service = FetchService(local_db)
                    try:
                        await local_fetch_service.fetch_from_source(sid)
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"Error background fetching source {sid}: {e}")

    asyncio.run(inner())

@router.post("/sync")
async def sync_dashboard(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Trigger background sync for all active sources"""
    sources_query = select(Source.id).where(Source.is_active == True)
    result = await db.execute(sources_query)
    source_ids = result.scalars().all()
    
    # Start sync in background
    background_tasks.add_task(run_sync_task, source_ids)
    
    # Return immediately with current data
    stats = await get_dashboard_stats(db, current_user)
    tenders = await get_recent_tenders(20, db, current_user)
    sources_status = await get_source_status_overview(db, current_user)

    last_log_query = select(FetchLog).where(FetchLog.status == FetchStatus.SUCCESS).order_by(desc(FetchLog.created_at)).limit(1)
    last_log_res = await db.execute(last_log_query)
    last_log = last_log_res.scalar_one_or_none()

    # Next sync times
    from app.core.scheduler import scheduler
    excel_job = scheduler.get_job("excel_auto_fetch")
    tender_job = scheduler.get_job("auto_tender_sync")

    now = datetime.now(timezone.utc)
    next_excel = (excel_job.next_run_time - now).total_seconds() / 60 if excel_job and excel_job.next_run_time else None
    next_tender_seconds = int((tender_job.next_run_time - now).total_seconds()) if tender_job and tender_job.next_run_time else None
    next_tender = (next_tender_seconds / 60) if next_tender_seconds is not None else None

    notif_query = select(Notification).where(Notification.user_id == current_user.id).order_by(desc(Notification.created_at)).limit(5)
    notif_res = await db.execute(notif_query)
    notifications = notif_res.scalars().all()

    return {
        "status": "sync_started",
        "message": f"Sync started in background for {len(source_ids)} sources.",
        "notifications": [
            {"id": n.id, "message": n.message, "isRead": n.is_read} for n in notifications
        ],
        "tenders": tenders,
        "topKeywords": stats.get("top_keywords", []),
        "sources": sources_status,
        "lastSyncAt": to_ist(last_log.created_at) if last_log else "Never",
        "nextExcelSync": f"{next_excel:.1f} min" if next_excel else "N/A",
        "nextTenderSync": f"{next_tender:.1f} min" if next_tender else "N/A",
        "nextTenderSyncSeconds": next_tender_seconds if next_tender_seconds is not None else None,
        "systemStatus": "System is active and monitoring",
        "stats": {
            "newTendersToday": stats.get("new_tenders_today", 0),
            "keywordMatches": stats.get("keyword_matches_today", 0),
            "activeSources": {"active": stats.get("active_sources", 0), "total": stats.get("total_sources", 0)},
            "alertsToday": stats.get("alerts_today", 0),
            "trendNewTenders": stats.get("new_tenders_change", 0),
            "trendKeywords": stats.get("keyword_matches_change", 0),
        }
    }


# ===========================
# DASHBOARD STATS
# ===========================
@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        # DB stores created_at in UTC. 
        # For "Today" stats in IST, midnight IST is 18:30 UTC the previous day.
        # But for simplicity, we'll use UTC day transitions for now.
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = today_start - timedelta(days=7)
        fourteen_days_ago = today_start - timedelta(days=14)
        thirty_days_ago = today_start - timedelta(days=30)

        # Build all queries
        q_total_tenders = select(func.count(Tender.id)).where(Tender.is_deleted == False)
        q_new_recent = select(func.count(Tender.id)).where(
            and_(Tender.created_at >= seven_days_ago, Tender.is_deleted == False)
        )
        q_new_previous = select(func.count(Tender.id)).where(
            and_(
                Tender.created_at >= fourteen_days_ago,
                Tender.created_at < seven_days_ago,
                Tender.is_deleted == False
            )
        )
        q_total_matches = select(func.count(TenderKeywordMatch.id))
        q_matched_recent = select(func.count(func.distinct(TenderKeywordMatch.tender_id))).where(
            TenderKeywordMatch.created_at >= seven_days_ago
        )
        q_matched_previous = select(func.count(func.distinct(TenderKeywordMatch.tender_id))).where(
            and_(
                TenderKeywordMatch.created_at >= fourteen_days_ago,
                TenderKeywordMatch.created_at < seven_days_ago
            )
        )
        q_active_sources = select(func.count(Source.id)).where(Source.is_active == True)
        q_total_sources = select(func.count(Source.id))
        q_total_notifications = select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == current_user.id,
                Notification.is_read == False,
                Notification.created_at >= today_start
            )
        )
        q_top_keywords = select(
            Keyword.keyword,
            Keyword.category,
            func.count(TenderKeywordMatch.id).label("match_count")
        ).join(TenderKeywordMatch).where(
            TenderKeywordMatch.created_at >= thirty_days_ago
        ).group_by(
            Keyword.id, Keyword.keyword, Keyword.category
        ).order_by(
            desc(func.count(TenderKeywordMatch.id))
        ).limit(5)

        # Execute sequentially (AsyncSession is NOT safe for concurrent calls)
        total_tenders = await db.scalar(q_total_tenders) or 0
        new_recent = await db.scalar(q_new_recent) or 0
        new_previous = await db.scalar(q_new_previous) or 0
        total_matches = await db.scalar(q_total_matches) or 0
        matched_recent = await db.scalar(q_matched_recent) or 0
        matched_previous = await db.scalar(q_matched_previous) or 0
        active_sources = await db.scalar(q_active_sources) or 0
        total_sources = await db.scalar(q_total_sources) or 0
        total_notifications = await db.scalar(q_total_notifications) or 0
        top_keywords_res = await db.execute(q_top_keywords)

        # Scheduler ETA
        from app.core.scheduler import scheduler
        tender_job = scheduler.get_job("auto_tender_sync")
        next_sync_seconds = None
        if tender_job and tender_job.next_run_time:
            next_sync_seconds = int((tender_job.next_run_time - datetime.now(timezone.utc)).total_seconds())

        new_change = 0.0
        if new_previous > 0:
            new_change = ((new_recent - new_previous) / new_previous) * 100

        matched_change = 0.0
        if matched_previous > 0:
            matched_change = ((matched_recent - matched_previous) / matched_previous) * 100

        top_keywords = [
            {
                "keyword": k[0],
                "category": k[1],
                "matches": int(k[2]) if k[2] is not None else 0
            }
            for k in top_keywords_res.all()
        ]

        return {
            "new_tenders_today": int(total_tenders),
            "new_tenders_change": round(float(new_change), 1) if new_change is not None else 0.0,
            "keyword_matches_today": int(total_matches),
            "keyword_matches_change": round(float(matched_change), 1) if matched_change is not None else 0.0,
            "active_sources": int(active_sources),
            "total_sources": int(total_sources),
            "alerts_today": int(total_notifications),
            "top_keywords": top_keywords,
            "next_tender_sync_in_seconds": next_sync_seconds
        }
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error in get_dashboard_stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dashboard stats error: {str(e)}")


# ===========================
# RECENT TENDERS
# ===========================
@router.get("/recent-tenders")
async def get_recent_tenders(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):

    result = await db.execute(
        select(
            Tender,
            Source.name.label("source_name")
        )
        .outerjoin(Source, Tender.source_id == Source.id)
        .options(
            joinedload(Tender.keyword_matches)
                .joinedload(TenderKeywordMatch.keyword),
        )
        .where(Tender.is_deleted == False)
        .order_by(desc(Tender.created_at))
        .limit(limit)
    )

    # Keep rows unique when eager-loading keyword_matches.
    tender_rows = result.unique().all()

    tender_list = []

    for t, source_name in tender_rows:

        status = t.status.lower() if t.status else "viewed"

        # ========================================================
        # FIX: Convert keywords array to comma-separated string
        # ========================================================
        keywords = [m.keyword.keyword for m in t.keyword_matches]
        keywords_string = ", ".join(keywords) if keywords else ""  # ← FIXED

        tender_list.append({
            "id": t.id,
            "title": t.title,
            "reference_id": t.reference_id,

            "agency_name": t.agency_name,
            "agency_location": t.agency_location,

            "source_name": source_name,

            "deadline_date": t.deadline_date,
            "days_until_deadline": t.days_until_deadline,

            "status": status,

            # ========================================================
            # FIX: Return comma-separated string instead of array
            # ========================================================
            "matched_keywords": keywords_string,  # ← FIXED (was: keywords)

            "description": t.description,
            "source_url": t.source_url,

            "attachments": t.attachments or [],

            "created_at": t.created_at.isoformat() + "Z" if t.created_at else None
        })

    return tender_list


# ===========================
# SOURCE STATUS
# ===========================
@router.get("/source-status")
async def get_source_status_overview(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):

    today_start = datetime.now().replace(hour=0, minute=0, second=0)

    #  FIX: Clean outer join (no or_)
    result = await db.execute(
        select(
            Source.name,
            func.count(Tender.id)
        )
        .outerjoin(
            Tender,
            and_(
                Tender.source_id == Source.id,
                Tender.created_at >= today_start
            )
        )
        .group_by(Source.name)
    )

    tender_counts = dict(result.all())

    result = await db.execute(
        select(
            Source.name,
            Source.status,
            Source.last_fetch_at
        )
        .where(Source.is_active == True)
    )

    sources = result.all()

    result_list = []

    for source_name, source_status, last_fetch_at in sources:

        count_today = tender_counts.get(source_name, 0)

        status_value = source_status.value if source_status else "UNKNOWN"

        result_list.append({

            "name": source_name,

            #  FIXED FIELD
            "status": status_value,

            "tenders_today": count_today,

            "last_fetch": (
                last_fetch_at.isoformat() + "Z"
                if last_fetch_at
                else None
            )
        })

    return result_list
