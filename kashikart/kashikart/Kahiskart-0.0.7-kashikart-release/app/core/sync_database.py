from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Use sync mysql driver
DATABASE_URL_SYNC = settings.DATABASE_URL.replace("+asyncmy", "+pymysql")

engine_sync = create_engine(
    DATABASE_URL_SYNC,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SyncSessionLocal = sessionmaker(bind=engine_sync)
