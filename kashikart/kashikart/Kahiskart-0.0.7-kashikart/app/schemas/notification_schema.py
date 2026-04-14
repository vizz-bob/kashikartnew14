# app/schemas/notification_schema.py

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, time
from enum import Enum


# --------------------------------------------------
# ENUMS
# --------------------------------------------------

class NotificationType(str, Enum):
    NEW_TENDER = "new_tender"
    KEYWORD_MATCH = "keyword_match"
    DEADLINE_APPROACHING = "deadline_approaching"
    SYSTEM_ERROR = "system_error"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    DESKTOP = "desktop"
    BOTH = "both"


# --------------------------------------------------
# BASE
# --------------------------------------------------

class NotificationBase(BaseModel):
    type: NotificationType
    channel: NotificationChannel
    title: str
    message: str


# --------------------------------------------------
# RESPONSE
# --------------------------------------------------

class NotificationResponse(NotificationBase):

    id: int
    user_id: int
    tender_id: Optional[int]
    module: str

    is_read: bool
    is_sent: bool

    email_sent: bool
    desktop_sent: bool

    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# --------------------------------------------------
# LIST
# --------------------------------------------------

class NotificationList(BaseModel):

    total: int
    unread_count: int
    items: List[NotificationResponse]


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

class NotificationSettings(BaseModel):

    enable_desktop: bool = True
    enable_email: bool = True

    email_recipients: List[EmailStr] = Field(default_factory=list)

    new_tender_published: bool = True
    keyword_match_found: bool = True
    deadline_approaching: bool = True
    system_errors: bool = False

    enable_silent_hours: bool = False
    silent_start_time: Optional[time]
    silent_end_time: Optional[time]

    class Config:
        from_attributes = True


class NotificationSettingsUpdate(BaseModel):
    # All fields optional for PATCH; defaults prevent 422 on partial updates
    enable_desktop: Optional[bool] = None
    enable_email: Optional[bool] = None

    email_recipients: Optional[List[str]] = None

    new_tender_published: Optional[bool] = None
    keyword_match_found: Optional[bool] = None
    deadline_approaching: Optional[bool] = None
    system_errors: Optional[bool] = None

    enable_silent_hours: Optional[bool] = None
    silent_start_time: Optional[time] = None
    silent_end_time: Optional[time] = None
