# run_service.py
import os
import sys

# Add base directory to sys.path manually so Python can find 'app'
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    base_path = os.path.dirname(sys.executable)
else:
    # Running normally
    base_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, base_path)

# Now this import will work correctly both in script and exe
from app.routes.sync_service import run_sync_service

if __name__ == "__main__":
    run_sync_service()
