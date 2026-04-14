import asyncio, logging, sys, os
logging.disable(logging.CRITICAL)
sys.path.append(os.getcwd())

from sqlalchemy import func, select
from app.core.database import AsyncSessionLocal
from app.models.tender import Tender
from app.models.source import Source
from app.models.keyword import Keyword, TenderKeywordMatch
from app.models.notification import Notification
import json

async def check():
    async with AsyncSessionLocal() as db:
        report = {}

        report["total_tenders"] = await db.scalar(select(func.count(Tender.id))) or 0
        report["total_sources"] = await db.scalar(select(func.count(Source.id))) or 0
        report["active_sources"] = await db.scalar(select(func.count(Source.id)).where(Source.is_active == True)) or 0
        report["total_keywords"] = await db.scalar(select(func.count(Keyword.id))) or 0
        report["total_matches"] = await db.scalar(select(func.count(TenderKeywordMatch.id))) or 0
        report["total_notifications"] = await db.scalar(select(func.count(Notification.id))) or 0

        result = await db.execute(select(Tender))
        tenders = result.scalars().all()
        report["tenders"] = []
        for t in tenders:
            report["tenders"].append({
                "id": t.id,
                "title": t.title,
                "status": str(t.status),
                "source_id": t.source_id,
                "created_at": str(t.created_at),
                "reference_id": t.reference_id,
                "agency_name": t.agency_name,
            })

        result = await db.execute(select(Source))
        sources = result.scalars().all()
        report["sources"] = []
        for s in sources:
            report["sources"].append({
                "id": s.id,
                "name": s.name,
                "is_active": s.is_active,
                "status": str(getattr(s, 'status', 'N/A')),
            })

        result = await db.execute(select(Keyword))
        keywords = result.scalars().all()
        report["keywords"] = []
        for k in keywords:
            report["keywords"].append({
                "id": k.id,
                "keyword": k.keyword,
                "category": str(k.category),
            })

        with open("dashboard_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        
        print("Report written to dashboard_report.json")

asyncio.run(check())
