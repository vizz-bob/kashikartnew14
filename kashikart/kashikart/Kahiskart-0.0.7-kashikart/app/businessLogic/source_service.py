import asyncio
import logging
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import AsyncSessionLocal
from app.models.source import Source
from app.businessLogic.fetch_service import FetchService

logger = logging.getLogger(__name__)


class SourceService:
    """
    Lightweight wrapper around FetchService so legacy callers can keep using
    SourceService while the heavy lifting (scraping, keyword matching, notifications)
    lives in FetchService.
    """

    @staticmethod
    async def fetch_from_source(
        db: AsyncSession,
        source_id: int,
        keywords: Optional[List[str]] = None
    ) -> Dict:
        fetch_service = FetchService(db)
        return await fetch_service.fetch_from_source(source_id, keywords=keywords)

    @staticmethod
    async def fetch_from_all_sources(
        db: AsyncSession,
        keywords: Optional[List[str]] = None,
        source_ids: Optional[List[int]] = None
    ) -> Dict:
        query = select(Source).where(Source.is_active == True)
        if source_ids:
            query = query.where(Source.id.in_(source_ids))

        result = await db.execute(query)
        sources = result.scalars().all()

        summary = {
            "total_sources": len(sources),
            "successful": 0,
            "failed": 0,
            "total_new_tenders": 0,
            "keywords_used": [k.strip() for k in (keywords or []) if k and k.strip()],
        }

        for source in sources:
            res = await SourceService.fetch_from_source(db, source.id, keywords=keywords)
            if res.get("error"):
                summary["failed"] += 1
            else:
                summary["successful"] += 1
                summary["total_new_tenders"] += res.get("new", res.get("new_tenders", 0))

        summary["success"] = summary["failed"] == 0
        return summary

    @staticmethod
    async def fetch_by_keywords(
        db: AsyncSession,
        keywords: List[str],
        source_ids: Optional[List[int]] = None
    ) -> Dict:
        """
        Run fetch only for tenders that match the provided keywords.
        If source_ids is provided, limit the fetch to that subset.
        """
        if not keywords:
            return {"error": "No keywords supplied", "success": False}

        return await SourceService.fetch_from_all_sources(
            db,
            keywords=keywords,
            source_ids=source_ids,
        )


# ----------------------------------------------------------------------
# Convenience wrappers for non-async callers (scheduler/CLI helpers)
# ----------------------------------------------------------------------
def fetch_from_source(
    source_id: int,
    keywords: Optional[List[str]] = None
) -> Dict:
    async def _run():
        async with AsyncSessionLocal() as db:
            return await SourceService.fetch_from_source(db, source_id, keywords=keywords)

    return asyncio.run(_run())


def fetch_from_all_sources(
    keywords: Optional[List[str]] = None,
    source_ids: Optional[List[int]] = None
) -> Dict:
    async def _run():
        async with AsyncSessionLocal() as db:
            return await SourceService.fetch_from_all_sources(
                db,
                keywords=keywords,
                source_ids=source_ids,
            )

    return asyncio.run(_run())


def fetch_by_keywords(
    keywords: List[str],
    source_ids: Optional[List[int]] = None
) -> Dict:
    async def _run():
        async with AsyncSessionLocal() as db:
            return await SourceService.fetch_by_keywords(db, keywords, source_ids)

    return asyncio.run(_run())
