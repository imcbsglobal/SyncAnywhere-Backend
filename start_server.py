# start_server.py
from app.main import app
import uvicorn
import subprocess
import os
import psutil
import sys
import logging
import time

def setup_startup_logging():
    """Setup basic logging for startup process"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger(__name__)

def launch_sync_service():
    logger = setup_startup_logging()
    exe_name = "SyncService.exe"

    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    exe_path = os.path.join(base_dir, exe_name)

    # Check if already running
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] and "SyncService.exe" in proc.info['name']:
                logger.info("🔄 SyncService already running (PID: %s)", proc.info['pid'])
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Launch it if not running
    if os.path.exists(exe_path):
        try:
            # Use CREATE_NEW_CONSOLE to run in separate window
            process = subprocess.Popen(
                [exe_path], 
                cwd=base_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            # Give it a moment to start
            time.sleep(2)
            
            # Verify it's running
            if process.poll() is None:
                logger.info("✅ SyncService launched successfully (PID: %s)", process.pid)
                return True
            else:
                logger.error("❌ SyncService failed to start properly")
                return False
                
        except Exception as e:
            logger.error("❌ Failed to launch SyncService: %s", str(e))
            return False
    else:
        logger.error("❌ SyncService.exe not found at: %s", exe_path)
        return False

def show_startup_info():
    logger = logging.getLogger(__name__)
    
    # Get current IP
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
    except:
        local_ip = "localhost"
    
    logger.info("=" * 60)
    logger.info("🌟 SYNCANYWHERE SERVER READY")
    logger.info("=" * 60)
    logger.info("🌐 Server URL: http://%s:8000", local_ip)
    logger.info("🌐 Local URL: http://localhost:8000")
    logger.info("📱 Mobile apps can connect to: %s:8000", local_ip)
    logger.info("📁 Check 'logs' folder for detailed logs")
    logger.info("🛑 Press Ctrl+C to stop the server")
    logger.info("=" * 60)

if __name__ == "__main__":
    logger = setup_startup_logging()
    
    logger.info("🚀 Starting SyncAnywhere System...")
    
    # Launch sync service first
    service_started = launch_sync_service()
    
    if not service_started:
        logger.warning("⚠️  SyncService might not be running properly")
        logger.info("🔄 Continuing with main server startup...")
    
    # Show startup information
    show_startup_info()
    
    # Start the main FastAPI server
    try:
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000, 
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error("❌ Server crashed: %s", str(e))
    finally:
        logger.info("🔚 SyncAnywhere server shutdown complete")