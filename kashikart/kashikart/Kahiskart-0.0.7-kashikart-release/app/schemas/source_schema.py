from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SourceStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"
    WARNING = "warning"


class LoginType(str, Enum):
    PUBLIC = "public"
    REQUIRED = "required"


class SourceBase(BaseModel):
    name: str = Field(..., max_length=255)
    url: str = Field(..., max_length=1000)
    description: Optional[str] = None
    login_type: LoginType = LoginType.PUBLIC


class SourceCreate(SourceBase):
    login_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None  # Will be encrypted
    scraper_type: str = Field("html", max_length=50)
    selector_config: Optional[Dict[str, Any]] = None


class SourceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = None
    description: Optional[str] = None
    login_type: Optional[LoginType] = None
    login_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    scraper_type: Optional[str] = None
    selector_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class SourceResponse(SourceBase):
    id: int
    status: SourceStatus
    is_active: bool
    total_tenders: int = 0
    last_fetch_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    consecutive_failures: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SourceList(BaseModel):
    total: int
    active: int
    disabled: int
    errors: int
    items: List[SourceResponse]


class SourceStats(BaseModel):
    total_sources: int
    active_sources: int
    disabled_sources: int
    error_sources: int