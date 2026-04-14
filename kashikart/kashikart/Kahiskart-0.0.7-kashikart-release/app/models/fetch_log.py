from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum


class FetchStatus(str, enum.Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


class FetchLog(Base):
    __tablename__ = "fetch_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Source Reference
    source_id = Column(Integer, ForeignKey("sources.id"))
    source_name = Column(String(255), index=True)

    # Fetch Information
    status = Column(Enum(FetchStatus), nullable=False, index=True)
    message = Column(Text, nullable=False)

    # Statistics
    tenders_found = Column(Integer, default=0)
    new_tenders = Column(Integer, default=0)
    updated_tenders = Column(Integer, default=0)

    # Error Details
    error_details = Column(Text)

    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    source = relationship("Source", back_populates="fetch_logs")

    def __repr__(self):
        return f"<FetchLog {self.source_name} - {self.status}>"