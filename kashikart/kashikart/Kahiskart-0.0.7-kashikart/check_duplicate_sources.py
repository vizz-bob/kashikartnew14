import asyncio
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.source import Source

async def check_duplicates():
    async with AsyncSessionLocal() as db:
        # Check for duplicate URLs
        stmt_url = select(Source.url, func.count(Source.id)).group_by(Source.url).having(func.count(Source.id) > 1)
        res_url = await db.execute(stmt_url)
        dupes_url = res_url.all()

        # Check for duplicate Names
        stmt_name = select(Source.name, func.count(Source.id)).group_by(Source.name).having(func.count(Source.id) > 1)
        res_name = await db.execute(stmt_name)
        dupes_name = res_name.all()

        with open('duplicate_sources_report.txt', 'w') as f:
            f.write("=== Duplicate URL Report ===\n")
            if dupes_url:
                for url, count in dupes_url:
                    f.write(f"URL: {url} | Count: {count}\n")
            else:
                f.write("No duplicate URLs found.\n")

            f.write("\n=== Duplicate Name Report ===\n")
            if dupes_name:
                for name, count in dupes_name:
                    f.write(f"Name: {name} | Count: {count}\n")
            else:
                f.write("No duplicate names found.\n")
        
        print("Duplicate report written to duplicate_sources_report.txt")

if __name__ == "__main__":
    asyncio.run(check_duplicates())
