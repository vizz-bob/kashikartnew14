import pandas as pd
import asyncio
import os
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.source import Source, LoginType, SourceStatus
from app.utils.encryption import encrypt_password

# File path from user
XLSX_PATH = r'C:\Users\katas\AppData\Local\Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm\LocalState\sessions\BE1CA8A7B43BD93E2F5923CF7764A13B18F621E4\transfers\2026-11\All Source Web Links (1).xlsx'

async def import_sources():
    try:
        df = pd.read_excel(XLSX_PATH)
        # Drop rows with no URL
        df = df.dropna(subset=['Web Source Data Link (Links of Tender Release Sources)'])
        print(f"Total rows to process: {len(df)}")

        async with AsyncSessionLocal() as db:
            # Get existing source names and URLs for de-duplication
            existing_res = await db.execute(select(Source.name, Source.url))
            existing_data = existing_res.all()
            existing_names = {row[0] for row in existing_data}
            existing_urls = {row[1] for row in existing_data}

            new_sources = 0
            updated_sources = 0

            for _, row in df.iterrows():
                url = str(row.get('Web Source Data Link (Links of Tender Release Sources)', '')).strip()
                name = str(row.get('Source', '')).strip()
                
                # Cleanup if Name is NaN/Empty
                if not name or name == 'nan':
                    # Try to extract name from URL or Remarks
                    remarks = str(row.get('Remarks', ''))
                    if remarks and remarks != 'nan':
                        name = remarks.split(',')[0][:50]
                    else:
                        name = url.split('//')[-1].split('/')[0]

                if url in existing_urls:
                    # Optional: Update existing? Skipping for now as per "add all sources" (implies missing)
                    # print(f"Skipping existing URL: {url}")
                    continue

                username = str(row.get('User', ''))
                if username == 'nan': username = None
                
                password = str(row.get('Password', ''))
                if password == 'nan': password = None
                
                login_req_str = str(row.get('User Login Required?', '')).lower()
                login_required = 'yes' in login_req_str
                login_type = LoginType.REQUIRED if login_required else LoginType.PUBLIC
                
                description = str(row.get('Remarks', ''))
                if description == 'nan': description = None

                new_src = Source(
                    name=name,
                    url=url,
                    description=description,
                    login_type=login_type,
                    login_required=login_required,
                    username=username,
                    password=password,
                    encrypted_password=encrypt_password(password) if password else None,
                    scraper_type="html", # Default
                    status=SourceStatus.ACTIVE,
                    is_active=True
                )
                db.add(new_src)
                new_sources += 1

            if new_sources > 0:
                await db.commit()
                print(f"Added {new_sources} new sources.")
            else:
                print("No new sources found to add.")

    except Exception as e:
        print(f"Error during import: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(import_sources())
