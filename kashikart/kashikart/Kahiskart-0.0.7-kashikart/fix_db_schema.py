import asyncio
from sqlalchemy import text
from app.core.database import engine

async def ensure_sources_schema(conn):
    result = await conn.execute(text("DESCRIBE sources"))
    existing_columns = {row[0] for row in result}

    if "login_required" not in existing_columns:
        print("Adding sources.login_required...")
        await conn.execute(
            text("ALTER TABLE sources ADD COLUMN login_required BOOLEAN NOT NULL DEFAULT 0")
        )

    if "password" not in existing_columns:
        print("Adding sources.password...")
        await conn.execute(
            text("ALTER TABLE sources ADD COLUMN password TEXT NULL")
        )

    if "is_healthy" not in existing_columns:
        print("Adding sources.is_healthy...")
        await conn.execute(
            text("ALTER TABLE sources ADD COLUMN is_healthy BOOLEAN NOT NULL DEFAULT 1")
        )


async def fix():
    async with engine.connect() as conn:
        print("Checking sources table...")
        await ensure_sources_schema(conn)

        print("Altering fetch_logs table...")
        await conn.execute(text("ALTER TABLE fetch_logs MODIFY message TEXT NULL"))
        await conn.execute(text("ALTER TABLE fetch_logs MODIFY source_name VARCHAR(255) NULL"))
        await conn.commit()
    print("Fix completed")

if __name__ == "__main__":
    asyncio.run(fix())
