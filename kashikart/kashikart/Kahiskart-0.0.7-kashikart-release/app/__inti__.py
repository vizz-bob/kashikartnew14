# backend/app/__init__.py
from app.main import app
# -------------------------
# Core system imports
# -------------------------
from .core.config import settings
from .core.database import engine, Base
from .core.scheduler import scheduler
from .core.security import verify_password  # Optional utility

# -------------------------
# Routers (for cleaner main.py imports)
# -------------------------
from .routers.auth import router as auth_router
from .routers.tenders import router as tenders_router
from .routers.keywords import router as keywords_router
from .routers.sources import router as sources_router
from .routers.fetch import router as fetch_router
from .routers.notifications import router as notifications_router

# -------------------------
# Services (business logic)
# -------------------------
from .businessLogic.tender_service import TenderService
from .businessLogic.keyword_service import KeywordService
from .businessLogic.source_service import SourceService
from .businessLogic.notification_service import NotificationService
from .businessLogic.change_detection_service import ChangeDetectionService

# -------------------------
# Utilities
# -------------------------
from .utils.encryption import EncryptionService
from .utils.logger import setup_logger
# from .utils.id_generator import generate_id

# -------------------------
# Notifications
# -------------------------
from .notifications.email import EmailNotificationService
from .notifications.desktop import DesktopNotificationService
from .notifications.email_sender import logger

# -------------------------
# Optional: Scraping & Keyword Engine
# -------------------------
from .scraping.base.scraper import BaseScraper
from .scraping.base.login_scraper import LoginScraper
from .scraping.implementations.html_scraper import HTMLScraper
from .scraping.implementations.pdf_scraper import PDFScraper
from .scraping.implementations.portal_scraper import PortalScraper
from .scraping.utils.session_manager import SessionManager
# from .scraping.utils.pagination import paginate
from .scraping.utils.date_normalizer import normalize_date
from .scraping.utils.text_cleaner import clean_text

from .keyword_engine.matcher import Matcher
from .keyword_engine.priority import Priority
# from .keyword_engine.document_parser import DocumentParser

# -------------------------
# Public API of the package
# -------------------------
__all__ = [
    # Core
    "settings", "engine", "Base", "scheduler", "verify_password",

    # Routers
    "auth_router", "tenders_router", "keywords_router", "sources_router",
    "fetch_router", "notifications_router",

    # Services
    "TenderService", "KeywordService", "SourceService", "NotificationService", "ChangeDetectionService",

    # Utilities
    "EncryptionService", "setup_logger", "generate_id",

    # Notifications
    "EmailNotificationService", "DesktopNotificationService", "logger",

    # Scraping
    "BaseScraper", "LoginScraper", "HTMLScraper", "PDFScraper", "PortalScraper",
    "SessionManager", "normalize_date", "clean_text",

    # Keyword Engine
    "Matcher", "Priority",
]
