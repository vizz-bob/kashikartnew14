from sqlalchemy import Column, BigInteger, String, Integer, JSON, TIMESTAMP, Enum, ForeignKey, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class FileStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"

class ExcelFileTracker(Base):
    __tablename__ = "excel_file_tracker"
    
    file_id = Column(BigInteger, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False)
    sheet_count = Column(Integer, nullable=True)
    uploaded_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    processed_at = Column(TIMESTAMP, nullable=True)
    status = Column(Enum(FileStatus), default=FileStatus.PENDING)
    file_hash = Column(String(255), unique=True, index=True)
    
    # Additional fields for tracking
    onedrive_file_id = Column(String(255), nullable=True)
    onedrive_etag = Column(String(255), nullable=True)  # For change detection
    last_modified = Column(TIMESTAMP, nullable=True)
    total_rows = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    sheets = relationship("RawExcelSheet", back_populates="file", cascade="all, delete-orphan")

class RawExcelSheet(Base):
    __tablename__ = "raw_excel_sheets"
    
    raw_id = Column(BigInteger, primary_key=True, autoincrement=True)
    file_id = Column(BigInteger, ForeignKey('excel_file_tracker.file_id', ondelete='CASCADE'), nullable=False)
    sheet_name = Column(String(255), nullable=False)
    row_number = Column(Integer, nullable=False)
    row_json = Column(JSON, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    # Additional metadata
    source_website = Column(String(255), nullable=True)  # Extracted from sheet name or data
    tender_id = Column(String(255), nullable=True, index=True)  # If available in data
    
    # Relationship
    file = relationship("ExcelFileTracker", back_populates="sheets")
    
    # Composite index for faster queries
    __table_args__ = (
        Index('idx_file_sheet', 'file_id', 'sheet_name'),
        Index('idx_created_at', 'created_at'),
    )

class OneDriveToken(Base):
    """Store Microsoft Graph API tokens securely"""
    __tablename__ = "onedrive_tokens"
    
    token_id = Column(BigInteger, primary_key=True, autoincrement=True)
    access_token = Column(Text, nullable=False)  # Encrypt in production
    refresh_token = Column(Text, nullable=True)  # Encrypt in production
    token_type = Column(String(50), default="Bearer")
    expires_at = Column(TIMESTAMP, nullable=False)
    scope = Column(String(500), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

class SheetHeaderMapping(Base):
    """Store header mappings for different tender websites"""
    __tablename__ = "sheet_header_mappings"
    
    mapping_id = Column(BigInteger, primary_key=True, autoincrement=True)
    sheet_name = Column(String(255), unique=True, nullable=False, index=True)
    source_website = Column(String(255), nullable=True)
    header_mapping = Column(JSON, nullable=False)  # {"original_header": "normalized_field"}
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Example: {"Tender No.": "tender_id", "Title": "title", "Due Date": "deadline"}