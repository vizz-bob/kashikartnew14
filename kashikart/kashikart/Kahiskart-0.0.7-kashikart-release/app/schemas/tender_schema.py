from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


class TenderStatus(str, Enum):
    NEW = "new"
    VIEWED = "viewed"
    SAVED = "saved"
    EXPIRED = "expired"


class AttachmentSchema(BaseModel):
    name: str
    url: str
    type: Optional[str] = None


class TenderBase(BaseModel):
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    agency_name: Optional[str] = Field(None, max_length=255)
    agency_location: Optional[str] = Field(None, max_length=255)
    published_date: Optional[date] = None
    deadline_date: Optional[date] = None
    source_url: Optional[str] = None


class TenderCreate(TenderBase):
    reference_id: str = Field(..., max_length=255)
    source_id: int
    attachments: Optional[List[Dict[str, Any]]] = None


class TenderUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    agency_name: Optional[str] = None
    agency_location: Optional[str] = None
    deadline_date: Optional[date] = None
    status: Optional[TenderStatus] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class TenderResponse(BaseModel):
    id: int
    title: str
    reference_id: Optional[str]
    agency_name: Optional[str]
    agency_location: Optional[str]

    # NEW
    source_name: Optional[str]

    deadline_date: Optional[datetime]
    days_until_deadline: Optional[int]

    status: Optional[str]
    description: Optional[str]
    published_date: Optional[datetime]

    keywords: List[str] = []

    # MAKE OPTIONAL
    source_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TenderList(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[TenderResponse]


class TenderFilter(BaseModel):
    status: Optional[str] = None
    source_id: Optional[int] = None
    keyword_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    search: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=100)