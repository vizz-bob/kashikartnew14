from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import List, Optional
from datetime import datetime, date, timedelta

from app.core.database import get_db
from app.models.tender import Tender
from app.models.source import Source
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.schemas.tender_schema import (
    TenderCreate, TenderUpdate, TenderResponse, TenderList, TenderFilter
)
import openpyxl
from io import BytesIO
from fastapi.responses import StreamingResponse
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
from sqlalchemy.orm import selectinload
from app.models.keyword import TenderKeywordMatch


router = APIRouter()


from sqlalchemy.orm import selectinload

@router.get("/", response_model=TenderList)
async def get_tenders(
    status: Optional[str] = Query(None),
    source_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    stmt = (
        select(Tender)
        .options(
            selectinload(Tender.keyword_matches).selectinload(
                TenderKeywordMatch.keyword
            )
        )
        .where(Tender.is_deleted == False)
    )

    # --------------------
    # Filters
    # --------------------

    if status:
        stmt = stmt.where(Tender.status == status)

    if source_id:
        stmt = stmt.where(Tender.source_id == source_id)

    if search:
        term = f"%{search}%"
        stmt = stmt.where(
            or_(
                Tender.title.ilike(term),
                Tender.reference_id.ilike(term),
                Tender.agency_name.ilike(term),
                Tender.description.ilike(term),
            )
        )

    if date_from:
        stmt = stmt.where(Tender.published_date >= date_from)

    if date_to:
        stmt = stmt.where(Tender.published_date <= date_to)

    # --------------------
    # Count
    # --------------------

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    # --------------------
    # Pagination
    # --------------------

    stmt = (
        stmt
        .order_by(Tender.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(stmt)
    tenders = result.scalars().unique().all()

    source_ids = {t.source_id for t in tenders if t.source_id is not None}
    source_name_map = {}
    source_default_keywords_map = {}
    if source_ids:
        source_rows = await db.execute(
            select(Source.id, Source.name, Source.selector_config).where(Source.id.in_(source_ids))
        )
        for sid, sname, scfg in source_rows.all():
            source_name_map[sid] = sname
            source_default_keywords_map[sid] = (scfg or {}).get('default_keywords', [])

    items = []

    today = date.today()

    for tender in tenders:

        # --------------------
        # Days left
        # --------------------

        days_left = None

        if tender.deadline_date:
            days_left = (tender.deadline_date - today).days

        # --------------------
        # Keywords
        # --------------------

        keyword_list = []

        for km in tender.keyword_matches or []:
            if km.keyword:
                keyword_list.append(km.keyword.keyword)

        if not keyword_list:
            keyword_list = source_default_keywords_map.get(tender.source_id, [])

        # --------------------
        # Build Response
        # --------------------

        item = {
            "id": tender.id,
            "title": tender.title,
            "reference_id": tender.reference_id,

            "agency_name": tender.agency_name or "N/A",
            "agency_location": tender.agency_location or "N/A",

            "source_name": source_name_map.get(tender.source_id, "Unknown"),

            "deadline_date": (
                tender.deadline_date.isoformat()
                if tender.deadline_date
                else None
            ),

            "days_until_deadline": days_left if days_left is not None else None,

            "status": tender.status,

            "description": tender.description or "",

            "keywords": keyword_list,

            "published_date": (
                tender.published_date.isoformat()
                if tender.published_date
                else None
            )
        }

        items.append(item)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items
    }

    

@router.get("/{tender_id}", response_model=TenderResponse)
async def get_tender(
        tender_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    stmt = (
        select(Tender)
        .where(
            Tender.id == tender_id,
            Tender.is_deleted == False
        )
    )

    result = await db.execute(stmt)
    tender = result.scalar_one_or_none()

    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found"
        )

    # Mark as viewed if new
    if tender.status == "new":
        tender.status = "viewed"
        await db.commit()

    source_name = await db.scalar(
        select(Source.name).where(Source.id == tender.source_id)
    )

    tender_dict = TenderResponse.model_validate(tender).model_dump()
    tender_dict["source_name"] = source_name

    return TenderResponse(**tender_dict)


@router.patch("/{tender_id}", response_model=TenderResponse)
async def update_tender(
        tender_id: int,
        tender_update: TenderUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    stmt = (
        select(Tender)
        .where(
            Tender.id == tender_id,
            Tender.is_deleted == False
        )
    )

    result = await db.execute(stmt)
    tender = result.scalar_one_or_none()

    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found"
        )

    # Apply updates
    update_data = tender_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(tender, field, value)

    await db.commit()
    await db.refresh(tender)

    source_name = await db.scalar(
        select(Source.name).where(Source.id == tender.source_id)
    )

    tender_dict = TenderResponse.model_validate(tender).model_dump()
    tender_dict["source_name"] = source_name

    return TenderResponse(**tender_dict)


@router.delete("/{tender_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tender(
        tender_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    stmt = select(Tender).where(Tender.id == tender_id)
    result = await db.execute(stmt)
    tender = result.scalar_one_or_none()

    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tender not found"
        )

    # Soft delete
    tender.is_deleted = True
    await db.commit()

    return None


@router.get("/export/excel")
async def export_tenders_excel(
    status: str | None = Query(None),
    source_id: int | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    stmt = (
        select(Tender)
        .options(
            joinedload(Tender.keyword_matches)      # <-- IMPORTANT FIX
        )
    )

    result = await db.execute(stmt)
    tenders = result.unique().scalars().all()

    if not tenders:
        df = pd.DataFrame([{
            "Message": "No tenders found in database"
        }])
    else:
        source_ids = {t.source_id for t in tenders if t.source_id is not None}
        source_name_map = {}
        if source_ids:
            source_rows = await db.execute(
                select(Source.id, Source.name).where(Source.id.in_(source_ids))
            )
            source_name_map = {sid: sname for sid, sname in source_rows.all()}

        data = []
        for t in tenders:
            data.append({
                "Tender ID": t.id,
                "Reference ID": t.reference_id,
                "Title": t.title,
                "Status": t.status,
                "Deadline": str(t.deadline_date) if t.deadline_date else None,

                # Convert relationship to readable text
                "Matched Keywords": [
                    km.keyword_id for km in (t.keyword_matches or [])
                ],

                "Source": source_name_map.get(t.source_id, "Unknown"),
                "Created At": t.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        df = pd.DataFrame(data)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Tenders")

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=tenders_export.xlsx"}
    )

# @router.get("/export/excel")
# async def export_tenders_excel(
#         status: Optional[str] = Query(None),
#         source_id: Optional[int] = Query(None),
#         date_from: Optional[date] = Query(None),
#         date_to: Optional[date] = Query(None),
#         db: Session = Depends(get_db),
#         current_user: User = Depends(get_current_user)
# ):
#     query = db.query(Tender).filter(Tender.is_deleted == False)

#     if status:
#         query = query.filter(Tender.status == status)
#     if source_id:
#         query = query.filter(Tender.source_id == source_id)
#     if date_from:
#         query = query.filter(Tender.published_date >= date_from)
#     if date_to:
#         query = query.filter(Tender.published_date <= date_to)

#     tenders = query.order_by(Tender.published_date.desc()).all()

#     # Create Excel workbook
#     wb = openpyxl.Workbook()
#     ws = wb.active
#     ws.title = "Tenders"

#     # Headers (matching your UI from image)
#     headers = [
#         "Title", "Reference ID", "Agency", "Location",
#         "Source", "Published Date", "Deadline",
#         "Days Until Deadline", "Status", "Description"
#     ]
#     ws.append(headers)

#     # Data rows
#     for tender in tenders:
#         ws.append([
#             tender.title,
#             tender.reference_id,
#             tender.agency_name or "",
#             tender.agency_location or "",
#             tender.source.name if tender.source else "",
#             tender.published_date.strftime("%Y-%m-%d") if tender.published_date else "",
#             tender.deadline_date.strftime("%Y-%m-%d") if tender.deadline_date else "",
#             tender.days_until_deadline if tender.days_until_deadline else "",
#             tender.status,
#             tender.description or ""
#         ])

#     # Save to BytesIO
#     output = BytesIO()
#     wb.save(output)
#     output.seek(0)

#     filename = f"tenders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

#     return StreamingResponse(
#         output,
#         media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         headers={"Content-Disposition": f"attachment; filename={filename}"}
#     )


@router.get("/stats/dashboard")
async def get_dashboard_stats(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    today = date.today()
    yesterday = today - timedelta(days=1)

    # New tenders today
    new_today_stmt = select(func.count(Tender.id)).where(
        func.date(Tender.created_at) == today,
        Tender.is_deleted == False
    )
    new_today = (await db.execute(new_today_stmt)).scalar() or 0

    # New tenders yesterday
    new_yesterday_stmt = select(func.count(Tender.id)).where(
        func.date(Tender.created_at) == yesterday,
        Tender.is_deleted == False
    )
    new_yesterday = (await db.execute(new_yesterday_stmt)).scalar() or 0

    # Calculate percentage change
    if new_yesterday > 0:
        change_percent = ((new_today - new_yesterday) / new_yesterday) * 100
    else:
        change_percent = 100 if new_today > 0 else 0

    # Keyword matches today
    # Assuming keyword_match_count is a column in Tender model based on usage
    # If not, we might need a join or different query. 
    # Based on original: Tender.keyword_match_count > 0
    # Let me check Tender model first to be safe, but fixing sync/async is priority.
    
    # Actually, let's use a subquery if keyword_match_count is not there.
    # Looking at original code, it expects keyword_match_count.
    from app.models.keyword import TenderKeywordMatch
    match_stmt = select(func.count(func.distinct(TenderKeywordMatch.tender_id))).where(
        func.date(TenderKeywordMatch.created_at) == today
    )
    keyword_matches = (await db.execute(match_stmt)).scalar() or 0

    # Active sources
    from app.models.source import Source
    active_sources_stmt = select(func.count(Source.id)).where(
        Source.is_active == True
    )
    active_sources = (await db.execute(active_sources_stmt)).scalar() or 0

    total_sources_stmt = select(func.count(Source.id))
    total_sources = (await db.execute(total_sources_stmt)).scalar() or 1

    return {
        "new_tenders_today": new_today,
        "change_from_yesterday": round(change_percent, 1),
        "keyword_matches": keyword_matches,
        "active_sources": f"{active_sources}/{total_sources}"
    }
