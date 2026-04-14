import asyncio
import os
import sys
import pandas as pd
from cryptography.fernet import Fernet
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.source import Source, LoginType
from sqlalchemy import select
from app.core.config import settings

def encrypt_password(password: str) -> str:
    if not password:
        return None
    try:
        f = Fernet(settings.ENCRYPTION_KEY.encode())
        return f.encrypt(str(password).encode()).decode()
    except Exception as e:
        print(f"Encryption error: {e}")
        return None

async def update_logins():
    file_path = 'uploads/All Source Web Links.xlsx'
    sheet_name = 'Source Links FL WA OR'
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"Reading {sheet_name}...")
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    
    # Logic:
    # Col 2: Source Name
    # Col 4: Username/Email
    # Col 5: Password
    # Col 7: Access Status
    # Col 8: Additional Notes/Auth Requirements
    
    async with AsyncSessionLocal() as db:
        updated = 0
        total_rows = len(df)
        
        for idx, row in df.iterrows():
            source_name = str(row.iloc[2]).strip()
            if not source_name or source_name.lower() == 'nan':
                continue
                
            username = str(row.iloc[4]).strip()
            password = str(row.iloc[5]).strip()
            access_field = str(row.iloc[7]).strip().lower()
            notes_field = str(row.iloc[8]).strip().lower() if len(row) > 8 else ""
            
            # Identify if login is needed
            needs_login = False
            
            # 1. Check if we have credentials
            has_creds = False
            if username and username.lower() not in ['nan', '-', 'none', '']:
                has_creds = True
            if password and password.lower() not in ['nan', '-', 'none', '']:
                has_creds = True
                
            if has_creds:
                needs_login = True
                
            # 2. Check access field for keywords
            login_keywords = ['restricted', 'not accessible', 'required', 'login', 'authentication', 'session']
            if any(k in access_field for k in login_keywords):
                needs_login = True
                
            # 3. Check notes field for keywords
            if any(k in notes_field for k in login_keywords):
                needs_login = True
            
            if needs_login:
                res = await db.execute(select(Source).where(Source.name == source_name))
                source = res.scalar_one_or_none()
                
                if source:
                    source.login_required = True
                    source.login_type = LoginType.REQUIRED
                    
                    if has_creds:
                        if username and username.lower() not in ['nan', '-', 'none', '']:
                            source.username = username
                        if password and password.lower() not in ['nan', '-', 'none', '']:
                            source.password = password
                            source.encrypted_password = encrypt_password(password)
                    
                    updated += 1
                    print(f"SET LOGIN REQUIRED: {source_name} (Reason: {'Creds' if has_creds else 'Access/Notes'})")
        
        await db.commit()
        print(f"DONE: Updated {updated} sources with login requirements.")

if __name__ == "__main__":
    asyncio.run(update_logins())
