from sqlalchemy import Column, Integer, Boolean, ForeignKey, Time, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class NotificationSettings(Base):

    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    enable_desktop = Column(Boolean, default=True)
    enable_email = Column(Boolean, default=True)

    email_recipients = Column(JSON, default=list)

    new_tender_published = Column(Boolean, default=True)
    keyword_match_found = Column(Boolean, default=True)
    deadline_approaching = Column(Boolean, default=True)
    system_errors = Column(Boolean, default=False)

    enable_silent_hours = Column(Boolean, default=False)

    silent_start_time = Column(Time, nullable=True)
    silent_end_time = Column(Time, nullable=True)

    user = relationship("User", back_populates="notification_settings")
