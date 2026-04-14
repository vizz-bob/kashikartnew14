import asyncio
import os
import sys
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.source import Source, LoginType
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Source).where(Source.name.ilike('%Demandstar%')))
        s = res.scalar_one_or_none()
        if s:
            print(f"FOUND {s.name}:")
            print(f"  login_required: {s.login_required}")
            print(f"  login_type: {s.login_type}")
            print(f"  username: {s.username}")
            print(f"  password: {s.password}")
            print(f"  encrypted_password: {s.encrypted_password[:20]}...")
        else:
            print("Demandstar NOT FOUND")

if __name__ == "__main__":
    asyncio.run(check())
