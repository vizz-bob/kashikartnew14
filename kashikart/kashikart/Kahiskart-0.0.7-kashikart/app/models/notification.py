from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum
from sqlalchemy import Index

class NotificationType(str, enum.Enum):
    NEW_TENDER = "new_tender"
    KEYWORD_MATCH = "keyword_match"
    DEADLINE_APPROACHING = "deadline_approaching"
    SYSTEM_ERROR = "system_error"


class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    DESKTOP = "desktop"
    BOTH = "both"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    # User Reference
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Tender Reference (optional)
    tender_id = Column(Integer, ForeignKey("tenders.id"))

    module = Column(String(50), nullable=False, index=True, default="dashboard")

    # Notification Details
    type = Column(Enum(NotificationType), nullable=False, index=True)
    channel = Column(Enum(NotificationChannel), default=NotificationChannel.BOTH)

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Status
    is_read = Column(Boolean, default=False, index=True)
    is_sent = Column(Boolean, default=False)

    # Delivery Status
    email_sent = Column(Boolean, default=False)
    desktop_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime)

    # Error Tracking
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="notifications")
    tender = relationship("Tender", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.type} - {self.title}>"

Index(
    "ix_notifications_user_module_read",
    Notification.user_id,
    Notification.module,
    Notification.is_read
)