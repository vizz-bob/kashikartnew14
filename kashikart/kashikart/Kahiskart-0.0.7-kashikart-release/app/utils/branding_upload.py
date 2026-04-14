import aiofiles
import uuid
import os

from fastapi import UploadFile, HTTPException
from pathlib import Path
from app.core.config import settings


UPLOAD_DIR = Path(settings.BRANDING_UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


# Validate logo (no magic, Railway safe)
async def validate_branding_image(file: UploadFile):

    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid image type")

    size = 0

    while chunk := await file.read(1024):
        size += len(chunk)

        if size > MAX_FILE_SIZE:
            await file.seek(0)
            raise HTTPException(status_code=400, detail="File too large")

    await file.seek(0)


# Save logo
async def save_branding_image(file: UploadFile):

    ext = os.path.splitext(file.filename)[1].lower()

    filename = f"branding_{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / filename

    async with aiofiles.open(path, "wb") as f:
        while chunk := await file.read(1024):
            await f.write(chunk)

    await file.seek(0)
    return filename


# Delete old logo
def delete_old_branding(filename: str | None):

    if not filename:
        return

    path = UPLOAD_DIR / filename

    if path.exists():
        path.unlink()


# Build public URL
def build_branding_url(filename: str | None):

    if not filename:
        return None

    return f"{settings.BACKEND_URL}/branding/{filename}"
