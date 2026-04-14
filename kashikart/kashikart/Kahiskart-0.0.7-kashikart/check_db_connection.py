import asyncio
import sys
import os

# Add the project root to sys.path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def check_connection():
    print("Testing database connection...")
    try:
        async with AsyncSessionLocal() as session:
            # Simple query to test connectivity
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            if value == 1:
                print("✅ Database connection successful!")
                
                # Check for table existence by selecting from a known table
                try:
                    res = await session.execute(text("SELECT count(*) FROM users"))
                    count = res.scalar()
                    print(f"✅ Found 'users' table. Total users: {count}")
                except Exception as e:
                    print(f"⚠️ 'users' table check failed (might not exist yet): {e}")

                try:
                    res = await session.execute(text("SELECT count(*) FROM sources"))
                    count = res.scalar()
                    print(f"✅ Found 'sources' table. Total sources: {count}")
                except Exception as e:
                    print(f"⚠️ 'sources' table check failed: {e}")
            else:
                print("❌ Database query returned unexpected value.")
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_connection())
