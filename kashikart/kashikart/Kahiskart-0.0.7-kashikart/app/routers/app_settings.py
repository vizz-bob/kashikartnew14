from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.app_settings import AppSettings

from app.auth.dependencies import get_current_superuser

from app.utils.branding_upload import (
    validate_branding_image,
    save_branding_image,
    delete_old_branding,
    build_branding_url
)

router = APIRouter(
    prefix="/api/app-settings",
    tags=["App Settings"]
)


#  PUBLIC API (Everyone)
@router.get("/")
async def get_app_settings(db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(AppSettings)
    )

    settings = result.scalars().first()

    if not settings:
        return {
            "app_name": "My App",
            "app_icon": None
        }

    return {
        "app_name": settings.app_name,
        "app_icon": build_branding_url(settings.app_icon)
    }


#  ADMIN API (Super Admin Only)
@router.put("/update")
async def update_app_settings(

    app_name: str | None = Form(None),
    icon: UploadFile | None = File(None),

    db: AsyncSession = Depends(get_db),

    superuser = Depends(get_current_superuser)
):

    if not app_name and not icon:
        return {"message": "Nothing to update"}

    try:
        result = await db.execute(
            select(AppSettings)
        )

        settings = result.scalars().first()

        if not settings:
            settings = AppSettings()
            db.add(settings)
            await db.flush()

        # Update name
        if app_name:
            settings.app_name = app_name

        # Update icon
        if icon:

            await validate_branding_image(icon)

            delete_old_branding(settings.app_icon)

            filename = await save_branding_image(icon)

            settings.app_icon = filename

        await db.commit()

        return {
            "message": "App settings updated successfully"
        }

    except Exception as e:

        await db.rollback()
        raise e
