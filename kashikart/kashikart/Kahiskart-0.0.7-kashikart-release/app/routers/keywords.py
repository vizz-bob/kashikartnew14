from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import func
from app.core.database import get_db
from app.models.keyword import Keyword, KeywordCategory, KeywordPriority
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.keyword_schema import (
    KeywordCreate, KeywordUpdate, KeywordResponse, KeywordList
)
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

router = APIRouter()


@router.get("/categories")
async def get_categories(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    """
    Get all available categories (predefined + custom ones from database)
    """
    # Get predefined categories
    predefined = Keyword.get_predefined_categories()

    # Get unique custom categories from database
    stmt = select(Keyword.category).where(
        Keyword.is_active == True
    ).distinct()

    result = await db.execute(stmt)
    db_categories = result.scalars().all()

    # Combine and remove duplicates
    all_categories = list(set(predefined + [cat for cat in db_categories if cat]))

    return {
        "predefined": predefined,
        "all": sorted(all_categories)
    }


@router.get("/active")
async def get_active_keywords(
        db: AsyncSession = Depends(get_db)
):
    """
    Get all active keywords as a simple list of strings.
    Used by frontend for keyword matching in Excel tenders.
    No authentication required for read-only public data.

    Returns: ["construction", "engineering", "infrastructure", ...]

    Example:
        GET /api/keywords/active
        Response: ["bridge", "construction", "engineering", "road", "water"]
    """
    stmt = select(Keyword.keyword).where(
        Keyword.is_active == True
    ).order_by(Keyword.keyword)

    result = await db.execute(stmt)
    keywords = result.scalars().all()

    # Return simple list of keyword strings (not objects)
    return keywords

@router.get("/", response_model=KeywordList)
async def get_keywords(
        # Filters
        search: Optional[str] = Query(None),
        category: Optional[str] = Query(None),  # Changed from KeywordCategory enum to str
        priority: Optional[KeywordPriority] = Query(None),

        # Pagination
        page: int = Query(1, ge=1),
        size: int = Query(10, ge=1, le=100),

        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    # Base query (only active)
    stmt = select(Keyword).where(Keyword.is_active.is_(True))

    # Apply filters
    if search:
        stmt = stmt.where(Keyword.keyword.ilike(f"%{search}%"))

    if category:
        stmt = stmt.where(Keyword.category == category)  # Now accepts any string

    if priority:
        stmt = stmt.where(Keyword.priority == priority)

    # Count (for pagination)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # Pagination
    offset = (page - 1) * size
    stmt = (
        stmt
        .order_by(Keyword.created_at.desc())
        .offset(offset)
        .limit(size)
    )

    # Fetch data
    result = await db.execute(stmt)
    keywords = result.scalars().all()

    pages = (total + size - 1) // size  # ceil

    return {
        "page": page,
        "size": size,
        "total": total,
        "pages": pages,
        "items": keywords
    }


@router.get("/{keyword_id}", response_model=KeywordResponse)
async def get_keyword(
        keyword_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Keyword).where(Keyword.id == keyword_id)
    )
    keyword = result.scalar_one_or_none()

    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keyword not found"
        )

    return keyword


@router.post("/", response_model=KeywordResponse, status_code=status.HTTP_201_CREATED)
async def create_keyword(
        keyword_data: KeywordCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # Check if keyword already exists
    stmt = select(Keyword).where(
        Keyword.keyword.ilike(keyword_data.keyword)
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keyword already exists"
        )

    keyword = Keyword(**keyword_data.dict())
    db.add(keyword)
    await db.commit()
    await db.refresh(keyword)

    return keyword


@router.patch("/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
        keyword_id: int,
        keyword_update: KeywordUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Keyword).where(Keyword.id == keyword_id)
    )
    keyword = result.scalar_one_or_none()

    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keyword not found"
        )

    for field, value in keyword_update.dict(exclude_unset=True).items():
        setattr(keyword, field, value)

    await db.commit()
    await db.refresh(keyword)

    return keyword


@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(
        keyword_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Keyword).where(Keyword.id == keyword_id)
    )
    keyword = result.scalar_one_or_none()

    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keyword not found"
        )

    # Soft delete
    keyword.is_active = False
    await db.commit()

    return None


@router.get("/stats/top")
async def get_top_keywords(
        limit: int = Query(5, ge=1, le=20),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Keyword)
        .where(Keyword.is_active == True)
        .order_by(Keyword.match_count.desc())
        .limit(limit)
    )

    keywords = result.scalars().all()

    return [
        {
            "keyword": k.keyword,
            "matches": k.match_count,
            "priority": k.priority
        }
        for k in keywords
    ]

@router.get("/search")
async def search_rows(
    keyword: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = text("""
        SELECT *
        FROM excel_row_raw
        WHERE JSON_SEARCH(row_data, 'one', :kw) IS NOT NULL
    """)

    result = await db.execute(query, {"kw": keyword})
    rows = result.mappings().all()

    return rows
