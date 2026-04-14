from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, and_, desc, select
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.tender import Tender
from app.models.source import Source
from app.models.keyword import Keyword, TenderKeywordMatch
from app.auth.dependencies import get_current_user


router = APIRouter(tags=["Dashboard"])


# ===========================
# DASHBOARD STATS
# ===========================
@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):

    today_start = datetime.now().replace(hour=0, minute=0, second=0)
    yesterday_start = today_start - timedelta(days=1)

    # New tenders
    new_today = await db.scalar(
        select(func.count(Tender.id))
        .where(Tender.created_at >= today_start)
    ) or 0

    new_yesterday = await db.scalar(
        select(func.count(Tender.id))
        .where(
            and_(
                Tender.created_at >= yesterday_start,
                Tender.created_at < today_start
            )
        )
    ) or 0

    new_change = 0
    if new_yesterday > 0:
        new_change = ((new_today - new_yesterday) / new_yesterday) * 100


    # Matched tenders
    matched_today = await db.scalar(
        select(func.count(func.distinct(Tender.id)))
        .join(TenderKeywordMatch)
        .where(Tender.created_at >= today_start)
    ) or 0


    matched_yesterday = await db.scalar(
        select(func.count(func.distinct(Tender.id)))
        .join(TenderKeywordMatch)
        .where(
            and_(
                Tender.created_at >= yesterday_start,
                Tender.created_at < today_start
            )
        )
    ) or 0


    matched_change = 0
    if matched_yesterday > 0:
        matched_change = (
            (matched_today - matched_yesterday) / matched_yesterday
        ) * 100


    # Sources
    active_sources = await db.scalar(
        select(func.count(Source.id))
        .where(Source.is_active == True)
    ) or 0

    total_sources = await db.scalar(
        select(func.count(Source.id))
    ) or 0


    alerts_today = new_today + matched_today


    # Top Keywords
    thirty_days_ago = today_start - timedelta(days=30)

    result = await db.execute(
        select(
            Keyword.keyword,
            Keyword.category,
            func.count(TenderKeywordMatch.id).label("match_count")
        )
        .join(TenderKeywordMatch)
        .where(TenderKeywordMatch.created_at >= thirty_days_ago)
        .group_by(Keyword.id, Keyword.keyword, Keyword.category)
        .order_by(desc("match_count"))
        .limit(5)
    )

    keywords_data = result.all()

    top_keywords = [
        {
            "keyword": k[0],
            "category": k[1],
            "matches": k[2]
        }
        for k in keywords_data
    ]


    return {
        "new_tenders_today": new_today,
        "new_tenders_change": round(new_change, 1),

        "keyword_matches_today": matched_today,
        "keyword_matches_change": round(matched_change, 1),

        "active_sources": active_sources,
        "total_sources": total_sources,

        "alerts_today": alerts_today,

        "top_keywords": top_keywords
    }


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
        select(Tender)
        .options(
            joinedload(Tender.source),
            joinedload(Tender.keyword_matches)
                .joinedload(TenderKeywordMatch.keyword),
        )
        .where(Tender.is_deleted == False)
        .order_by(desc(Tender.created_at))
        .limit(limit)
    )

    #  FIX: unique() added
    tenders = result.unique().scalars().all()

    tender_list = []

    for t in tenders:

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

            "source_name": t.source.name if t.source else None,

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

            "created_at": t.created_at
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
        select(Source)
        .where(Source.is_active == True)
    )

    sources = result.scalars().all()

    result_list = []

    for s in sources:

        count_today = tender_counts.get(s.name, 0)

        result_list.append({

            "name": s.name,

            #  FIXED FIELD
            "status": s.status or "UNKNOWN",

            "tenders_today": count_today,

            "last_fetch": (
                s.last_fetch_at.isoformat()
                if s.last_fetch_at
                else None
            )
        })

    return result_list