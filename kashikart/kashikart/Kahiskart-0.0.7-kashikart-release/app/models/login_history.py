from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class LoginHistory(Base):
    __tablename__ = "login_history"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    ip_address = Column(String(50))
    user_agent = Column(String(255))

    status = Column(String(20))  # success / failed

    login_time = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
