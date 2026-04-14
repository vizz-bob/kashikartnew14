from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy import func
from typing import Optional
from datetime import datetime
import json

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from cryptography.fernet import Fernet
from base64 import urlsafe_b64encode
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings

from app.models.source import Source, SourceStatus
from app.models.tender import Tender
from app.models.user import User

from app.auth.dependencies import get_current_user
from app.schemas.source_schema import (
    SourceCreate,
    SourceUpdate,
    SourceResponse,
    SourceList,
    SourceStats
)

router = APIRouter()

SAFE_SOURCE_FIELDS = (
    Source.id,
    Source.name,
    Source.url,
    Source.description,
    Source.login_type,
    Source.login_url,
    Source.username,
    Source.encrypted_password,
    Source.scraper_type,
    Source.selector_config,
    Source.status,
    Source.is_active,
    Source.total_tenders,
    Source.last_fetch_at,
    Source.last_success_at,
    Source.consecutive_failures,
    Source.created_at,
    Source.updated_at,
)


# ======================================================
# 🔐 Encryption Utils
# ======================================================

def get_cipher():
    key = settings.SECRET_KEY[:32].encode().ljust(32, b"0")
    return Fernet(urlsafe_b64encode(key))


def encrypt_password(password: str) -> str:
    cipher = get_cipher()
    return cipher.encrypt(password.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    cipher = get_cipher()
    return cipher.decrypt(encrypted.encode()).decode()




class RegisterFileRequest(BaseModel):
    path: str


def _normalize_selector_config(raw_value):
    """Accept dict or JSON string and always return a dict."""
    if raw_value is None:
        return {}

    if isinstance(raw_value, dict):
        return raw_value

    if isinstance(raw_value, str):
        value = raw_value.strip()
        if not value:
            return {}

        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as e:
            raise HTTPException(422, f"Invalid selector_config JSON: {e}")

        # Handle double-stringified JSON payloads like '"{...}"'
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except json.JSONDecodeError as e:
                raise HTTPException(422, f"Invalid selector_config JSON: {e}")

        if not isinstance(parsed, dict):
            raise HTTPException(422, "selector_config must be a JSON object")

        return parsed

    raise HTTPException(422, "selector_config must be an object or JSON string")




@router.get("/", response_model=SourceList)
async def get_sources(

    # Filters
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),

    # Pagination
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=1000),

    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    stmt = select(Source).options(load_only(*SAFE_SOURCE_FIELDS))
    count_stmt = select(func.count(Source.id))

    # Apply filters
    if search:
        stmt = stmt.where(Source.name.ilike(f"%{search}%"))
        count_stmt = count_stmt.where(Source.name.ilike(f"%{search}%"))

    if status:
        stmt = stmt.where(Source.status == status)
        count_stmt = count_stmt.where(Source.status == status)

    # Count
    total = (await db.execute(count_stmt)).scalar()

    # Pagination
    offset = (page - 1) * size

    stmt = (
        stmt
        .order_by(Source.created_at.desc())
        .offset(offset)
        .limit(size)
    )

    result = await db.execute(stmt)
    sources = result.scalars().all()

    # Compute actual tender counts from the tenders table
    tender_count_stmt = (
        select(Tender.source_id, func.count(Tender.id).label("count"))
        .where(Tender.is_deleted == False)
        .group_by(Tender.source_id)
    )
    tender_count_result = await db.execute(tender_count_stmt)
    tender_counts = dict(tender_count_result.all())

    # Sync total_tenders on each source with the real count
    for source in sources:
        real_count = tender_counts.get(source.id, 0)
        if source.total_tenders != real_count:
            source.total_tenders = real_count
    await db.commit()

    # Accurate DB stats
    active_stmt = select(func.count()).where(
        Source.is_active == True,
        Source.status == SourceStatus.ACTIVE
    )

    disabled_stmt = select(func.count()).where(
        Source.is_active == False
    )

    error_stmt = select(func.count()).where(
        Source.status == SourceStatus.ERROR
    )

    active = (await db.execute(active_stmt)).scalar()
    disabled = (await db.execute(disabled_stmt)).scalar()
    errors = (await db.execute(error_stmt)).scalar()

    pages = (total + size - 1) // size

    return {
        "page": page,
        "size": size,
        "total": total,
        "pages": pages,

        "active": active,
        "disabled": disabled,
        "errors": errors,

        "items": sources
    }




@router.get("/stats", response_model=SourceStats)
async def get_source_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    total = (await db.execute(
        select(func.count(Source.id))
    )).scalar()

    active = (await db.execute(
        select(func.count(Source.id)).where(
            Source.is_active == True,
            Source.status == SourceStatus.ACTIVE
        )
    )).scalar()

    disabled = (await db.execute(
        select(func.count(Source.id)).where(
            Source.is_active == False
        )
    )).scalar()

    errors = (await db.execute(
        select(func.count(Source.id)).where(
            Source.status == SourceStatus.ERROR
        )
    )).scalar()

    return {
        "total_sources": total,
        "active_sources": active,
        "disabled_sources": disabled,
        "error_sources": errors
    }


# ======================================================
# 🔍 Get Single Source
# ======================================================

@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    stmt = (
        select(Source)
        .options(load_only(*SAFE_SOURCE_FIELDS))
        .where(Source.id == source_id)
    )

    source = (await db.execute(stmt)).scalar_one_or_none()

    if not source:
        raise HTTPException(404, "Source not found")

    return source




@router.post("/", response_model=SourceResponse, status_code=201)
async def create_source(
    source_data: SourceCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    exists = (await db.execute(
        select(Source)
        .options(load_only(*SAFE_SOURCE_FIELDS))
        .where(Source.url == source_data.url)
    )).scalars().first()

    if exists:
        raise HTTPException(400, "Source with this URL already exists")

    data = source_data.model_dump(exclude={"password"})
    data["selector_config"] = _normalize_selector_config(data.get("selector_config"))

    if source_data.password:
        data["encrypted_password"] = encrypt_password(source_data.password)

    source = Source(**data)

    db.add(source)
    await db.commit()
    await db.refresh(source)

    # Trigger immediate fetch
    from app.scheduler.jobs import fetch_single_source_job
    background_tasks.add_task(fetch_single_source_job, source.id)

    return source




@router.patch("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: int,
    source_update: SourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    stmt = (
        select(Source)
        .options(load_only(*SAFE_SOURCE_FIELDS))
        .where(Source.id == source_id)
    )
    source = (await db.execute(stmt)).scalar_one_or_none()

    if not source:
        raise HTTPException(404, "Source not found")

    data = source_update.model_dump(exclude_unset=True, exclude={"password"})
    if "selector_config" in data:
        data["selector_config"] = _normalize_selector_config(data.get("selector_config"))

    if source_update.password:
        data["encrypted_password"] = encrypt_password(source_update.password)

    for k, v in data.items():
        setattr(source, k, v)

    await db.commit()
    await db.refresh(source)

    return source




@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    stmt = (
        select(Source)
        .options(load_only(*SAFE_SOURCE_FIELDS))
        .where(Source.id == source_id)
    )
    source = (await db.execute(stmt)).scalar_one_or_none()

    if not source:
        raise HTTPException(404, "Source not found")

    tender_stmt = select(func.count(Tender.id)).where(
        Tender.source_id == source_id
    )

    tender_count = (await db.execute(tender_stmt)).scalar()

    if tender_count > 0:
        raise HTTPException(
            400,
            f"Cannot delete source with {tender_count} tenders"
        )

    await db.delete(source)
    await db.commit()

    return None




@router.post("/{source_id}/toggle", response_model=SourceResponse)
async def toggle_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    stmt = (
        select(Source)
        .options(load_only(*SAFE_SOURCE_FIELDS))
        .where(Source.id == source_id)
    )
    source = (await db.execute(stmt)).scalar_one_or_none()

    if not source:
        raise HTTPException(404, "Source not found")

    source.is_active = not source.is_active

    source.status = (
        SourceStatus.ACTIVE
        if source.is_active
        else SourceStatus.DISABLED
    )

    await db.commit()
    await db.refresh(source)

    return source




@router.post("/{source_id}/refresh")
async def refresh_source(
    source_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    stmt = select(Source).where(Source.id == source_id)
    source = (await db.execute(stmt)).scalar_one_or_none()

    if not source:
        raise HTTPException(404, "Source not found")

    # Update timestamp
    source.last_fetch_at = datetime.utcnow()

    await db.commit()
    await db.refresh(source)

    # Run fetch in background
    try:
        from app.scheduler.jobs import fetch_single_source_job
        background_tasks.add_task(fetch_single_source_job, source_id)
    except Exception:
        pass

    return {
        "message": "Refresh started",
        "source_id": source_id,
        "last_fetch": source.last_fetch_at
    }




@router.post("/register-file")
async def register_excel_file(
    data: RegisterFileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    path = data.path.replace("\\", "/").strip('\'"')

    return {
        "status": "registered",
        "path": path,
        "message": "Excel file registered successfully"
    }
