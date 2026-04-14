import asyncio
import os
import sys
import pandas as pd
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.source import Source, LoginType, SourceStatus
from sqlalchemy import select
from cryptography.fernet import Fernet
from app.core.config import settings

def encrypt_password(password: str) -> str:
    if not password:
        return None
    try:
        f = Fernet(settings.ENCRYPTION_KEY.encode())
        return f.encrypt(password.encode()).decode()
    except Exception as e:
        print(f"Encryption error: {e}")
        return None

async def update_source_credentials():
    file_path = 'uploads/All Source Web Links.xlsx'
    sheet_name = 'Source Links FL WA OR'
    
    if not os.path.exists(file_path):
        print("File not found")
        return

    print(f"Reading {sheet_name}...")
    # Use index-based access to avoid column name mismatch issues
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    
    # Column mapping (based on debug output)
    # Index 2: Source Name
    # Index 4: Username
    # Index 5: Password
    # Index 7: Access Type
    
    async with AsyncSessionLocal() as db:
        updated_count = 0
        not_found = []
        
        for _, row in df.iterrows():
            source_name = str(row.iloc[2]).strip()
            username = str(row.iloc[4]).strip()
            password = str(row.iloc[5]).strip()
            access_type = str(row.iloc[7]).strip().lower()
            
            if not source_name or source_name.lower() == 'nan':
                 continue
                 
            # Find source in DB
            res = await db.execute(select(Source).where(Source.name == source_name))
            source = res.scalar_one_or_none()
            
            if source:
                has_creds = False
                # Update credentials
                u = str(row.iloc[4]).strip()
                p = str(row.iloc[5]).strip()
                
                if p and p.lower() != 'nan' and p != '-':
                    source.password = p
                    source.encrypted_password = encrypt_password(p)
                    has_creds = True
                    
                if u and u.lower() != 'nan' and u != '-':
                    source.username = u
                    has_creds = True
                    
                # Update access type
                if has_creds or "restricted" in access_type or "not accessible" in access_type:
                    source.login_type = LoginType.REQUIRED
                    source.login_required = True
                    print(f"Set REQUIRED for {source.name} (has_creds: {has_creds}, access: {access_type})")
                else:
                    source.login_type = LoginType.PUBLIC
                    source.login_required = False
                    
                updated_count += 1
            else:
                not_found.append(source_name)
        
        await db.commit()
        print(f"DONE: Updated credentials for {updated_count} sources.")
        if not_found:
            print(f"Sources NOT found in DB ({len(not_found)}): {not_found[:5]}...")

if __name__ == "__main__":
    asyncio.run(update_source_credentials())
