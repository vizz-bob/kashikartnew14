import aiofiles
import uuid
import os

from fastapi import UploadFile, HTTPException
from pathlib import Path

from app.core.config import settings


# Upload directory from .env
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE

# Allowed image extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


async def validate_image(file: UploadFile):
    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid image type")

    # Validate size
    size = 0

    while chunk := await file.read(1024):
        size += len(chunk)

        if size > MAX_FILE_SIZE:
            await file.seek(0)
            raise HTTPException(status_code=400, detail="File too large")

    await file.seek(0)


async def save_upload_file(file: UploadFile, user_id: int):
    ext = os.path.splitext(file.filename)[1].lower()
    filename = f"{user_id}_{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / filename

    async with aiofiles.open(path, "wb") as f:
        while chunk := await file.read(1024):
            await f.write(chunk)

    await file.seek(0)
    return filename


def delete_old_profile_picture(filename: str):
    if not filename:
        return

    path = UPLOAD_DIR / filename

    if path.exists():
        path.unlink()


def build_profile_url(filename: str | None):
    if not filename:
        return None

    return f"{settings.BACKEND_URL}/uploads/{filename}"
