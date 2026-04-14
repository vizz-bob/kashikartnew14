from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, update
from typing import Optional, Dict

from app.core.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.schemas.notification_schema import (
    NotificationResponse,
    NotificationList,
    NotificationSettings,
    NotificationSettingsUpdate
)
from app.models.notification_settings import NotificationSettings as NotificationSettingsModel


router = APIRouter()


# --------------------------------------------------
# CENTRAL MODULE LIST
# --------------------------------------------------
VALID_MODULES = [
    "dashboard",
    "tenders",
    "keywords",
    "sources",
    "notifications",
    "analytics",
    "system-logs"
]


# --------------------------------------------------
# GET ALL NOTIFICATIONS - OPTIMIZED QUERY (PERF IMPROVEMENT)
# --------------------------------------------------
# Added unread_count subquery for single-query performance
@router.get("/", response_model=NotificationList)
async def get_notifications(
    module: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),

    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    stmt = select(Notification).where(
        Notification.user_id == current_user.id
    )

    # Filter by module
    if module:
        if module not in VALID_MODULES:
            raise HTTPException(400, "Invalid module")

        stmt = stmt.where(Notification.module == module)

    # Filter read/unread
    if is_read is not None:
        stmt = stmt.where(Notification.is_read == is_read)

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()

    # Unread count
    unread_stmt = select(func.count(Notification.id)).where(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    )
    unread_count = (await db.execute(unread_stmt)).scalar() # Perf opt: direct field count

    # Pagination
    offset = (page - 1) * page_size

    stmt = (
        stmt
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(stmt)
    notifications = result.scalars().all()

    # Manually serialize to include 'Z' suffix for UTC
    serialized_items = []
    for n in notifications:
        item = NotificationResponse.from_orm(n).dict()
        if n.created_at:
            item["created_at"] = n.created_at.isoformat() + "Z"
        if n.sent_at:
            item["sent_at"] = n.sent_at.isoformat() + "Z"
        serialized_items.append(item)

    return {
        "total": total,
        "unread_count": unread_count,
        "items": serialized_items
    }


# --------------------------------------------------
# MARK SINGLE READ
# --------------------------------------------------
@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )

    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(404, "Notification not found")

    notification.is_read = True

    await db.commit()
    await db.refresh(notification)

    return notification


# --------------------------------------------------
# MARK ALL READ (FAST VERSION)
# --------------------------------------------------
@router.post("/mark-all-read")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    stmt = (
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
        .values(is_read=True)
    )

    result = await db.execute(stmt)
    await db.commit()

    return {
        "message": "All notifications marked as read",
        "updated_count": result.rowcount
    }


# --------------------------------------------------
# DELETE
# --------------------------------------------------
@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )

    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(404, "Notification not found")

    await db.delete(notification)
    await db.commit()

    return {"message": "Notification deleted"}


# --------------------------------------------------
# GET SETTINGS
# --------------------------------------------------

@router.get("/settings", response_model=NotificationSettings)
async def get_notification_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    result = await db.execute(
        select(NotificationSettingsModel)
        .where(NotificationSettingsModel.user_id == current_user.id)
    )

    settings = result.scalar_one_or_none()

    # Create default if missing
    if not settings:

        settings = NotificationSettingsModel(
            user_id=current_user.id
        )

        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return settings


# --------------------------------------------------
# UPDATE SETTINGS
# --------------------------------------------------

@router.patch("/settings", response_model=NotificationSettings)
async def update_notification_settings(
    settings_update: NotificationSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    result = await db.execute(
        select(NotificationSettingsModel)
        .where(NotificationSettingsModel.user_id == current_user.id)
    )

    settings = result.scalar_one_or_none()

    # Create if missing
    if not settings:

        settings = NotificationSettingsModel(
            user_id=current_user.id
        )

        db.add(settings)

    # Apply updates
    data = settings_update.model_dump(exclude_unset=True)

    for key, value in data.items():
        setattr(settings, key, value)

    await db.commit()
    await db.refresh(settings)

    return settings



# --------------------------------------------------
# PAGE-SPECIFIC
# --------------------------------------------------
@router.get("/page/{module}", response_model=NotificationList)
async def get_page_notifications(
    module: str,
    is_read: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),

    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if module not in VALID_MODULES:
        raise HTTPException(400, "Invalid module")

    stmt = select(Notification).where(
        Notification.user_id == current_user.id,
        Notification.module == module
    )

    if is_read is not None:
        stmt = stmt.where(Notification.is_read == is_read)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()

    unread_stmt = select(func.count()).where(
        Notification.user_id == current_user.id,
        Notification.module == module,
        Notification.is_read == False
    )
    unread_count = (await db.execute(unread_stmt)).scalar()

    offset = (page - 1) * page_size

    stmt = (
        stmt
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(stmt)
    items = result.scalars().all()

    # Manually serialize to include 'Z' suffix for UTC
    serialized_items = []
    for n in items:
        item = NotificationResponse.from_orm(n).dict()
        if n.created_at:
            item["created_at"] = n.created_at.isoformat() + "Z"
        if n.sent_at:
            item["sent_at"] = n.sent_at.isoformat() + "Z"
        serialized_items.append(item)

    return {
        "total": total,
        "unread_count": unread_count,
        "items": serialized_items
    }


# --------------------------------------------------
# UNREAD COUNTS (ALL MODULES)
# --------------------------------------------------
@router.get("/unread-counts", response_model=Dict[str, int])
async def get_all_unread_counts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    counts = {}

    for module in VALID_MODULES:

        stmt = select(func.count()).where(
            Notification.user_id == current_user.id,
            Notification.module == module,
            Notification.is_read == False
        )

        counts[module] = (await db.execute(stmt)).scalar()

    total_stmt = select(func.count()).where(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    )

    counts["total"] = (await db.execute(total_stmt)).scalar()

    return counts
