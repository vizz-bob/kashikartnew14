from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum


class SourceStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"
    WARNING = "warning"


class LoginType(str, enum.Enum):
    PUBLIC = "public"
    REQUIRED = "required"


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)

    # Basic Information
    name = Column(String(255), nullable=False, index=True)
    url = Column(String(1000), nullable=False)
    description = Column(Text)

    # Login Requirements
    login_type = Column(Enum(LoginType), default=LoginType.PUBLIC)
    login_url = Column(String(1000))
    username = Column(String(255))
    encrypted_password = Column(Text)  # Encrypted password

    # Scraping Configuration
    scraper_type = Column(String(50), default="html")  # html, pdf, portal
    selector_config = Column(JSON)  # CSS selectors and parsing rules

    # Status
    status = Column(Enum(SourceStatus), default=SourceStatus.ACTIVE, index=True)
    is_active = Column(Boolean, default=True)

    # Statistics
    total_tenders = Column(Integer, default=0)
    last_fetch_at = Column(DateTime)
    last_success_at = Column(DateTime)
    consecutive_failures = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenders = relationship("Tender", back_populates="source", cascade="all, delete-orphan")
    fetch_logs = relationship("FetchLog", back_populates="source", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Source {self.name} ({self.status})>"