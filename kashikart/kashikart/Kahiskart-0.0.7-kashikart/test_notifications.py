#!/usr/bin/env python3
'''
Test Email & Desktop Notifications Directly
Run: cd kashikart/Kahiskart-0.0.7-kashikart && python test_notifications.py
'''

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db  # Reuse engine
from app.notifications.email import EmailNotificationService, send_email_notification
from app.notifications.desktop import send_desktop_notification, DesktopNotificationService
from app.core.config import settings
from app.utils.logger import setup_logger
from app.models.tender import Tender  # Mock
from app.models.keyword import Keyword  # Mock

logger = setup_logger('test_notifications')

async def test_email():
    print('🧪 Testing Email Notifications...')
    service = EmailNotificationService()
    
    # Mock data
    mock_tender = type('MockTender', (), {
        'title': 'Test Tender - Road Construction Project',
        'agency_name': 'PWD Maharashtra',
        'reference_id': 'MH/PWD/2024/001',
        'deadline': '2024-12-15',
        'location': 'Nagpur',
        'description': 'Construction of 10km highway...',
        'source_url': 'https://example.com/tender'
    })()
    
    mock_keywords = [type('MockKeyword', (), {'keyword': 'road construction'})()]
    
    success = await service.send_new_tender_notification(
        tender=mock_tender,
        matched_keywords=mock_keywords,
        recipients=[settings.SMTP_USER]  # Send to self
    )
    
    print(f'✅ Email Test: {"SUCCESS" if success else "FAILED"}')
    return success

async def test_desktop():
    print('🧪 Testing Desktop Notifications...')
    service = DesktopNotificationService()
    service.send_notification(
        title='🎉 Test Desktop Notification',
        message='This is a test from Tender Intel system!',
        timeout=8
    )
    print('✅ Desktop Test: SENT (check your system tray)')
    return True

async def main():
    print('🚀 Starting Notification Tests')
    print(f'SMTP Config: {settings.SMTP_USER} @ {settings.SMTP_HOST}:{settings.SMTP_PORT}')
    
    email_ok = await test_email()
    desktop_ok = await test_desktop()
    
    if email_ok and desktop_ok:
        print('\n🎊 ALL TESTS PASSED! Notifications working.')
    else:
        print('\n❌ Some tests failed. Check logs above.')
    
    print('\n💡 Next: Start backend with `uvicorn app.main:app --reload`')
    print('   Run scrapers: `python run_scraper_debug.py`')
    print('   Check /api/notifications/ endpoint')

if __name__ == '__main__':
    asyncio.run(main())

