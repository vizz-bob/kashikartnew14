import asyncio
from sqlalchemy import text
from app.core.database import engine

async def fix():
    async with engine.connect() as conn:
        print("Fixing fetch_logs status enum...")
        try:
            # We use VARCHAR to avoid ENUM issues if the values keep changing
            await conn.execute(text("ALTER TABLE fetch_logs MODIFY COLUMN status VARCHAR(50) NOT NULL"))
            print("Changed status to VARCHAR(50)")
        except Exception as e:
            print(f"Error altering fetch_logs: {e}")

        print("Fixing sources status enum...")
        try:
            await conn.execute(text("ALTER TABLE sources MODIFY COLUMN status VARCHAR(50) NOT NULL"))
            print("Changed sources.status to VARCHAR(50)")
        except Exception as e:
            print(f"Error altering sources: {e}")

        await conn.commit()
    print("Fix completed")

if __name__ == "__main__":
    asyncio.run(fix())
