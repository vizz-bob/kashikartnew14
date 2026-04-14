import asyncio
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def check_connection():
    output = []
    output.append("Testing database connection...")
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            if value == 1:
                output.append("SUCCESS: Database connection verified via 'SELECT 1'")
                
                try:
                    res = await session.execute(text("SELECT count(*) FROM users"))
                    count = res.scalar()
                    output.append(f"SUCCESS: 'users' table access verified. Total users: {count}")
                except Exception as e:
                    output.append(f"WARNING: 'users' table check failed: {str(e)}")

                try:
                    res = await session.execute(text("SELECT count(*) FROM sources"))
                    count = res.scalar()
                    output.append(f"SUCCESS: 'sources' table access verified. Total sources: {count}")
                except Exception as e:
                    output.append(f"WARNING: 'sources' table check failed: {str(e)}")
            else:
                output.append("FAILURE: Database query returned unexpected value.")
    except Exception as e:
        output.append(f"FAILURE: Database connection failed: {str(e)}")

    with open("db_check_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    print("Check completed. Results written to db_check_result.txt")

if __name__ == "__main__":
    asyncio.run(check_connection())
