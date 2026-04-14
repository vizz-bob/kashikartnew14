import asyncio
import os
import sys
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.keyword_engine.matcher import KeywordMatcher

async def refresh_all_matches():
    print("Initializing Keyword Matcher...")
    async with AsyncSessionLocal() as db:
        matcher = KeywordMatcher(db)
        print("Rebuilding all keyword matches... this might take a moment.")
        results = await matcher.rebuild_all_matches()
        print(f"DONE: {results}")

if __name__ == "__main__":
    asyncio.run(refresh_all_matches())
