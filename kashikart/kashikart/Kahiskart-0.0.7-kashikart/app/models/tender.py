from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Date,
    Text,
    ForeignKey,
    JSON,
)


class Tender(Base):
    __tablename__ = "tenders"

    id = Column(Integer, primary_key=True, index=True)

    # --------------------
    # BASIC INFORMATION
    # --------------------
    title = Column(String(500), nullable=False, index=True)

    reference_id = Column(
        String(500),
        unique=True,
        index=True,
        nullable=False
    )

    description = Column(Text)

    # --------------------
    # AGENCY & LOCATION
    # --------------------
    agency_name = Column(String(255), index=True)

    agency_location = Column(String(255))

    # --------------------
    # DATES
    # --------------------
    published_date = Column(Date, index=True)

    deadline_date = Column(Date, index=True)

    # --------------------
    # SOURCE
    # --------------------
    source_id = Column(
        Integer,
        ForeignKey("sources.id"),
        nullable=False
    )

    source_url = Column(String(1000))

    # --------------------
    # STATUS
    # --------------------
    status = Column(
        String(50),
        default="new",
        index=True
    )

    # --------------------
    # ATTACHMENTS
    # --------------------
    attachments = Column(JSON)

    # --------------------
    # EXCEL IMPORT TRACKING ✅ NEW
    # --------------------
    imported_from_excel = Column(
        Boolean,
        default=False,
        index=True
    )

    excel_row_id = Column(
        Integer,
        unique=True,
        index=True,
        nullable=True
    )

    raw_excel_data = Column(
        JSON,
        nullable=True
    )

    # --------------------
    # CHANGE TRACKING
    # --------------------
    content_hash = Column(String(64), index=True)

    version = Column(Integer, default=1)

    # --------------------
    # METADATA
    # --------------------
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    is_deleted = Column(Boolean, default=False, index=True)

    # --------------------
    # RELATIONSHIPS
    # --------------------
    source = relationship(
        "Source",
        back_populates="tenders"
    )

    notifications = relationship(
        "Notification",
        back_populates="tender",
        cascade="all, delete-orphan"
    )

    keyword_matches = relationship(
        "TenderKeywordMatch",
        back_populates="tender",
        cascade="all, delete-orphan"
    )

    # --------------------
    # HELPERS
    # --------------------
    def __repr__(self):
        return f"<Tender {self.reference_id}: {self.title[:50]}>"

    @property
    def days_until_deadline(self):
        if self.deadline_date:
            return (
                self.deadline_date
                - datetime.utcnow().date()
            ).days
        return None

    @property
    def is_expired(self):
        if self.deadline_date:
            return (
                self.deadline_date
                < datetime.utcnow().date()
            )
        return False
