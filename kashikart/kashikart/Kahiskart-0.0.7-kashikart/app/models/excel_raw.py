from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class ExcelFile(Base):
    __tablename__ = "excel_file"

    id = Column(Integer, primary_key=True)
    file_path = Column(String(500), nullable=False, unique=True)
    last_modified = Column(DateTime)
    checksum = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)

    sheets = relationship("ExcelSheet", back_populates="excel_file")


class ExcelSheet(Base):
    __tablename__ = "excel_sheet"

    id = Column(Integer, primary_key=True)
    excel_file_id = Column(Integer, ForeignKey("excel_file.id"))
    sheet_name = Column(String(255), nullable=False)
    source_name = Column(String(255))
    row_count = Column(Integer, default=0)
    last_processed_at = Column(DateTime)
    status = Column(String(50), default="ACTIVE")

    excel_file = relationship("ExcelFile", back_populates="sheets")
    rows = relationship("ExcelRowRaw", back_populates="sheet")


class ExcelRowRaw(Base):
    __tablename__ = "excel_row_raw"

    id = Column(Integer, primary_key=True)
    sheet_id = Column(Integer, ForeignKey("excel_sheet.id"))
    row_index = Column(Integer)
    row_data = Column(JSON, nullable=False)
    row_hash = Column(String(64), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    sheet = relationship("ExcelSheet", back_populates="rows")
