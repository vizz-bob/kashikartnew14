from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime, date


class DashboardStatsResponse(BaseModel):
    """Dashboard statistics"""
    new_tenders_today: int
    new_tenders_change: float
    keyword_matches_today: int
    keyword_matches_change: float
    active_sources: int
    total_sources: int
    alerts_today: int
    top_keywords: List[dict]


class SourceStatusOverview(BaseModel):
    """Source status for dashboard"""
    name: str
    status: str
    tenders_today: int
    last_fetch: Optional[datetime]


class RecentTenderSummary(BaseModel):
    """Simplified tender for dashboard display"""
    id: int
    tender_id: str
    title: str
    agency_name: Optional[str]
    source_name: str
    publish_date: Optional[datetime]
    deadline: Optional[datetime]
    status_badge: str

    class Config:
        from_attributes = True
