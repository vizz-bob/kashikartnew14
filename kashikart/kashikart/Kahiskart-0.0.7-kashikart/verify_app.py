import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

try:
    from app.main import app
    print("Main app loaded successfully")
except Exception as e:
    import traceback
    traceback.print_exc()
