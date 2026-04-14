from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.auth.dependencies import get_current_superuser

from app.models.login_history import LoginHistory
from app.models.user import User

from fastapi import Query
from datetime import datetime

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"]
)


@router.get("/logins")
async def get_all_logins(
    db: AsyncSession = Depends(get_db),
    _ = Depends(get_current_superuser),

    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),

    email: str | None = None,
    status: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
):

    if status and status not in ["success", "failed"]:
        return {"error": "Invalid status. Use success or failed"}

    offset = (page - 1) * size

    query = (
        select(
            LoginHistory.id,
            LoginHistory.login_time,
            LoginHistory.ip_address,
            LoginHistory.status,
            LoginHistory.user_agent,

            User.id.label("user_id"),
            User.email,
            User.full_name,
        )
        .join(User, User.id == LoginHistory.user_id)
    )

    if email:
        query = query.where(User.email.ilike(f"%{email}%"))

    if status:
        query = query.where(LoginHistory.status == status)

    try:
        if from_date:
            query = query.where(
                LoginHistory.login_time >= datetime.fromisoformat(from_date)
            )
    except ValueError:
        pass

    try:
        if to_date:
            query = query.where(
                LoginHistory.login_time <= datetime.fromisoformat(to_date)
            )
    except ValueError:
        pass

    query = (
        query
        .order_by(LoginHistory.login_time.desc())
        .offset(offset)
        .limit(size)
    )

    result = await db.execute(query)
    rows = result.all()

    # Count
    count_query = (
        select(LoginHistory.id)
        .join(User, User.id == LoginHistory.user_id)
    )

    if email:
        count_query = count_query.where(User.email.ilike(f"%{email}%"))

    if status:
        count_query = count_query.where(LoginHistory.status == status)

    total = len((await db.execute(count_query)).all())

    return {
        "page": page,
        "size": size,
        "total": total,

        "data": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "email": r.email,
                "full_name": r.full_name,
                "ip_address": r.ip_address,
                "user_agent": r.user_agent,
                "status": r.status,
                "login_time": r.login_time,
            }
            for r in rows
        ]
    }



@router.put("/block-user/{user_id}")
async def block_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _ = Depends(get_current_superuser)
):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if not user:
        return {"error": "User not found"}

    user.is_blocked = True
    await db.commit()

    return {"message": "User blocked successfully"}


@router.put("/unblock-user/{user_id}")
async def unblock_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _ = Depends(get_current_superuser)
):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if not user:
        return {"error": "User not found"}

    user.is_blocked = False
    await db.commit()

    return {"message": "User unblocked successfully"}


@router.get("/users")
async def get_all_users(
    db: AsyncSession = Depends(get_db),
    _ = Depends(get_current_superuser),


    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),

    is_blocked: bool | None = None,
    email: str | None = None,
):

    offset = (page - 1) * size

    query = select(User)

    # Filters
    if is_blocked is not None:
        query = query.where(User.is_blocked == is_blocked)

    if email:
        query = query.where(User.email.ilike(f"%{email}%"))

    # Pagination
    query = query.offset(offset).limit(size)

    result = await db.execute(query)

    users = result.scalars().all()

    # Count
    count_q = select(User.id)

    if is_blocked is not None:
        count_q = count_q.where(User.is_blocked == is_blocked)

    total = len((await db.execute(count_q)).all())

    return {
        "page": page,
        "size": size,
        "total": total,

        "data": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "is_blocked": u.is_blocked,
                "is_active": u.is_active,
                "is_verified": u.is_verified,
                "last_login": u.last_login,
                "created_at": u.created_at,
            }
            for u in users
        ]
    }
