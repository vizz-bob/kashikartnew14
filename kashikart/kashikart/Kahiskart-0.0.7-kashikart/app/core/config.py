# from pydantic_settings import BaseSettings
# from typing import Optional


# class Settings(BaseSettings):
#     # Application
#     APP_NAME: str = "Tender Intel"
#     APP_VERSION: str = "1.0.0"
#     # API Configuration
#     API_V1_PREFIX: str = "/api/v1"
#     ENVIRONMENT: str = "development"

#     FRONTEND_URL: str = "http://localhost:3000"

#     # Database
#     DATABASE_URL: str
#     DATABASE_HOST: str = "localhost"
#     DATABASE_PORT: int = 3306
#     DATABASE_USER: str = "root"
#     DATABASE_PASSWORD: str
#     DATABASE_NAME: str = "tender_db"

#     # Security
#     SECRET_KEY: str
#     ALGORITHM: str = "HS256"
#     ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
#     ENCRYPTION_KEY: str

#     # Email (Gmail)
#     SMTP_HOST: str = "smtp.gmail.com"
#     SMTP_PORT: int = 587
#     SMTP_USER: str
#     SMTP_PASSWORD: str
#     SMTP_FROM_EMAIL: str
#     SMTP_FROM_NAME: str = "Tender Intel"
#     SMTP_TLS: bool = True  # Added for TLS support

#     # Scraping
#     SCRAPING_TIMEOUT: int = 30
#     MAX_CONCURRENT_SCRAPES: int = 5
#     USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

#     # Notifications
#     ENABLE_DESKTOP_NOTIFICATIONS: bool = True
#     ENABLE_EMAIL_NOTIFICATIONS: bool = True

#     # Scheduler
#     SCHEDULER_TIMEZONE: str = "US/Eastern"
#     DEFAULT_FETCH_INTERVAL_HOURS: int = 6
    
#     # OneDrive Configuration
#     ONEDRIVE_SHARE_LINK: str = "https://d.docs.live.net/EC66F8CFBC81D65B/Desktop/All%20Source%20Web%20Links%20(1)%20(1).xlsx"
#     ONEDRIVE_POLL_INTERVAL: int = 300  # 5 minutes
    
#     # Microsoft Graph API (Optional - for authenticated access)
#     MICROSOFT_CLIENT_ID: Optional[str] = None
#     MICROSOFT_CLIENT_SECRET: Optional[str] = None
#     MICROSOFT_TENANT_ID: str = "common"
    
#     # Processing Configuration
#     BATCH_SIZE: int = 1000  # Process rows in batches
#     MAX_WORKERS: int = 4  # Concurrent processing threads

#     UPLOAD_DIR: str
#     BRANDING_UPLOAD_DIR: str
#     MAX_UPLOAD_SIZE: int = 5_242_880
#     BACKEND_URL: str
    
    
#     # CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]

#     class Config:
#         env_file = ".env"
#         case_sensitive = True


# settings = Settings()

import os
import sys
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


def _resolve_env_file() -> str:
    # In PyInstaller builds, use the executable directory so dist/.env is loaded.
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve().parent / ".env")
    return str(Path(__file__).resolve().parents[2] / ".env")


# Load .env if present so SMTP/DB credentials can be overridden locally
ENV_FILE_PATH = _resolve_env_file()
if Path(ENV_FILE_PATH).exists():
    load_dotenv(ENV_FILE_PATH, override=False)
elif Path(".env").exists():
    # Fallback when scripts are run from project root (cwd)
    load_dotenv(".env", override=False)


class Settings(BaseSettings):
    # ------------------------------------------------------------------
    # App
    # ------------------------------------------------------------------
    APP_NAME: str = "Tender Intel"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    DATABASE_URL: str = "sqlite+aiosqlite:///./tender_dev.db"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 3306
    DATABASE_USER: str = "root"
    DATABASE_PASSWORD: str = ""
    DATABASE_NAME: str = "tender_dev"

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    SECRET_KEY: str = "super-secret-key-change-in-production!!"
    ENCRYPTION_KEY: str = "SGVsbG8gV29ybGQhMTIzNDU2Nzg5MDEyMzQ1Njc4OTA=="
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ------------------------------------------------------------------
    # Email (Gmail)
    # ------------------------------------------------------------------
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "ankursati75956@gmail.com"
    SMTP_PASSWORD: str = "buyppybrlzsnozjz"
    SMTP_FROM_EMAIL: str = "ankursati75956@gmail.com"
    SMTP_FROM_NAME: str = "Tender Intel"
    SMTP_TLS: bool = True

    # ------------------------------------------------------------------
    # File Uploads
    # ------------------------------------------------------------------
    UPLOAD_DIR: str = "uploads"
    BRANDING_UPLOAD_DIR: str = "branding"
    MAX_UPLOAD_SIZE: int = 5_242_880  # 5 MB

    # ------------------------------------------------------------------
    # Scraping
    # ------------------------------------------------------------------
    SCRAPING_TIMEOUT: int = 30
    MAX_CONCURRENT_SCRAPES: int = 5
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    ENABLE_DESKTOP_NOTIFICATIONS: bool = True
    ENABLE_EMAIL_NOTIFICATIONS: bool = True

    # ------------------------------------------------------------------
    # Scheduler
    # ------------------------------------------------------------------
    SCHEDULER_TIMEZONE: str = "US/Eastern"
    DEFAULT_FETCH_INTERVAL_HOURS: int = 6

    # ------------------------------------------------------------------
    # OneDrive
    # ------------------------------------------------------------------
    # ONEDRIVE_SHARE_LINK: str
    # ONEDRIVE_POLL_INTERVAL: int = 300  # 5 minutes
    ONEDRIVE_SHARE_LINK: str = "https://d.docs.live.net/EC66F8CFBC81D65B/Desktop/All%20Source%20Web%20Links%20(1)%20(1).xlsx"
    ONEDRIVE_POLL_INTERVAL: int = 300  # 5 minutes

    # Microsoft Graph (optional)
    MICROSOFT_CLIENT_ID: Optional[str] = None
    MICROSOFT_CLIENT_SECRET: Optional[str] = None
    MICROSOFT_TENANT_ID: str = "common"

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------
    BATCH_SIZE: int = 1000
    MAX_WORKERS: int = 4

    # ------------------------------------------------------------------
    # Pydantic Settings Config (v2)
    # ------------------------------------------------------------------
    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
