from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from app.core.database import Base

class ExcelIngestionMeta(Base):
    __tablename__ = "excel_ingestion_meta"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    file_path = Column(Text, nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
