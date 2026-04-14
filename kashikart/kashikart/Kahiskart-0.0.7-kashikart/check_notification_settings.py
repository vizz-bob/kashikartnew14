import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.notification_settings import NotificationSettings
from sqlalchemy import select

async def check():
    users_data = []
    settings_data = []
    try:
        async with AsyncSessionLocal() as db:
            # Users
            res_users = await db.execute(select(User))
            users = res_users.scalars().all()
            for u in users:
                users_data.append({
                    'id': u.id,
                    'email': u.email,
                    'is_verified': u.is_verified,
                    'is_active': u.is_active,
                    'is_superuser': u.is_superuser
                })
            
            # Notification settings
            res_settings = await db.execute(select(NotificationSettings))
            settings = res_settings.scalars().all()
            for s in settings:
                settings_data.append({
                    'user_id': s.user_id,
                    'enable_email': s.enable_email,
                    'enable_desktop': s.enable_desktop,
                    'email_recipients': s.email_recipients,
                    'new_tender_published': s.new_tender_published,
                    'keyword_match_found': s.keyword_match_found
                })
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("=== USERS ===")
    print(f"Total users: {len(users_data)}")
    for data in users_data:
        print(data)
    
    print("\n=== NOTIFICATION SETTINGS ===")
    print(f"Total settings: {len(settings_data)}")
    for data in settings_data:
        print(data)

if __name__ == "__main__":
    asyncio.run(check())

