from sqlalchemy import Column, Integer, String
from app.core.database import Base


class AppSettings(Base):

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)

    app_name = Column(String(100), nullable=True)

    app_icon = Column(String(255), nullable=True)
