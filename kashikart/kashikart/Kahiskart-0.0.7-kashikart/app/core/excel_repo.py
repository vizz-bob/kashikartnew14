from app.core.database import SessionLocal
from sqlalchemy import text

def get_excel_path():
    db = SessionLocal()
    query = text("SELECT file_path FROM excel_file ORDER BY id DESC LIMIT 1")
    result = db.execute(query).fetchone()
    db.close()
    return result[0] if result else None
