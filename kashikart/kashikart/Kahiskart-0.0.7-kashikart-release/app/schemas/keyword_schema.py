from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class KeywordPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class KeywordCategory(str, Enum):
    """Predefined categories - kept for reference and UI dropdowns"""
    INFORMATION_TECHNOLOGY = "Information Technology"
    CONSTRUCTION = "Construction"
    HEALTHCARE = "Healthcare"
    ENVIRONMENTAL = "Environmental"
    SERVICES = "Services"
    OTHER = "Other"


class KeywordBase(BaseModel):
    keyword: str = Field(..., min_length=2, max_length=255)
    category: str = Field(default="Other", min_length=1, max_length=100)  # Changed to str
    priority: KeywordPriority = KeywordPriority.MEDIUM
    enable_alerts: bool = True

    @validator('category')
    def validate_category(cls, v):
        """Strip whitespace and ensure non-empty"""
        if not v or not v.strip():
            return "Other"
        return v.strip()

    @validator('keyword')
    def validate_keyword(cls, v):
        """Strip whitespace from keyword"""
        return v.strip()


class KeywordCreate(KeywordBase):
    pass


class KeywordUpdate(BaseModel):
    keyword: Optional[str] = Field(None, min_length=2, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=100)  # Changed to str
    priority: Optional[KeywordPriority] = None
    enable_alerts: Optional[bool] = None
    is_active: Optional[bool] = None

    @validator('category')
    def validate_category(cls, v):
        """Strip whitespace if provided"""
        if v is not None:
            if not v.strip():
                raise ValueError("Category cannot be empty")
            return v.strip()
        return v

    @validator('keyword')
    def validate_keyword(cls, v):
        """Strip whitespace if provided"""
        if v is not None:
            return v.strip()
        return v


class KeywordResponse(KeywordBase):
    id: int
    match_count: int = 0
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KeywordList(BaseModel):
    page: int  # Added from your router
    size: int  # Added from your router
    total: int
    pages: int  # Added from your router
    items: List[KeywordResponse]


class CategoryResponse(BaseModel):
    """Response model for categories endpoint"""
    predefined: List[str]
    all: List[str]