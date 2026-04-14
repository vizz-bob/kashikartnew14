import sys
import os
import requests

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.scraping.utils.session_manager import SessionManager
from app.models.source import Source

def test_session():
    print("Testing SessionManager...")
    try:
        source = Source(id=1, name="Test Source", url="https://www.google.com")
        session = SessionManager.get_session(source)
        print(f"✅ Session acquired: {type(session)}")
        
        response = session.get("https://www.google.com")
        print(f"✅ Request successful! Status code: {response.status_code}")
        
        SessionManager.close_all_sessions()
        print("✅ All sessions closed.")
    except Exception as e:
        print(f"❌ SessionManager test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_session()
