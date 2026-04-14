from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class FileStatusEnum(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"

class FileTrackerResponse(BaseModel):
    file_id: int
    file_name: str
    sheet_count: Optional[int] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    status: FileStatusEnum
    file_hash: str
    total_rows: Optional[int] = 0
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True

class SheetDataResponse(BaseModel):
    raw_id: int
    file_id: int
    sheet_name: str
    row_number: int
    row_json: Dict[str, Any]
    source_website: Optional[str] = None
    tender_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProcessFileRequest(BaseModel):
    share_link: Optional[str] = None
    force_refresh: bool = False

class ProcessFileResponse(BaseModel):
    success: bool
    message: str
    file_tracker: Optional[FileTrackerResponse] = None

class GetDataRequest(BaseModel):
    file_id: Optional[int] = None
    sheet_name: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)

class GetDataResponse(BaseModel):
    total_count: int
    data: List[SheetDataResponse]
    file_info: Optional[FileTrackerResponse] = None

class SheetListResponse(BaseModel):
    file_id: int
    sheets: List[str]

class HeaderMappingResponse(BaseModel):
    sheet_name: str
    source_website: Optional[str]
    header_mapping: Dict[str, str]
    
    class Config:
        from_attributes = True

class TenderDataResponse(BaseModel):
    """Normalized tender data response"""
    tender_id: Optional[str]
    title: Optional[str]
    organization: Optional[str]
    deadline: Optional[str]
    publish_date: Optional[str]
    value: Optional[str]
    status: Optional[str]
    category: Optional[str]
    location: Optional[str]
    source_website: Optional[str]
    sheet_name: str
    raw_data: Dict[str, Any]
    created_at: datetime

class PowerBIDataResponse(BaseModel):
    """Formatted response for Power BI consumption"""
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    last_updated: datetime
    total_records: int

class StatisticsResponse(BaseModel):
    """Statistics about processed data"""
    total_files: int
    total_sheets: int
    total_rows: int
    files_by_status: Dict[str, int]
    rows_by_source: Dict[str, int]
    latest_update: Optional[datetime]