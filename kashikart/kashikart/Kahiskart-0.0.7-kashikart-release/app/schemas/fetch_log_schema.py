from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class FetchStatus(str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


class FetchLogBase(BaseModel):
    source_id: Optional[int] = None
    source_name: str = Field(..., max_length=255)
    status: FetchStatus
    message: str


class FetchLogCreate(FetchLogBase):
    tenders_found: int = 0
    new_tenders: int = 0
    updated_tenders: int = 0
    error_details: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None


class FetchLogResponse(FetchLogBase):
    id: int
    tenders_found: int
    new_tenders: int
    updated_tenders: int
    error_details: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FetchLogList(BaseModel):
    total: int
    success_count: int
    warning_count: int
    error_count: int
    info_count: int
    items: List[FetchLogResponse]


class FetchLogFilter(BaseModel):
    status: Optional[FetchStatus] = None
    source_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=100)