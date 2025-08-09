# start_server.py
from app.main import app
import uvicorn
import subprocess
import os
import psutil
import sys
import logging
import time
from app.db_utils import get_all_local_ips, get_best_local_ip

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
    
    # Get all available IPs
    all_ips = get_all_local_ips()
    primary_ip = get_best_local_ip()
    
    logger.info("=" * 80)
    logger.info("🌟 SYNCANYWHERE SERVER READY")
    logger.info("=" * 80)
    logger.info("📡 PRIMARY SERVER IP: %s:8000", primary_ip)
    logger.info("🌐 LOCAL ACCESS: http://localhost:8000")
    logger.info("")
    logger.info("📱 MOBILE APP CONNECTION OPTIONS:")
    for ip in all_ips:
        logger.info("   • http://%s:8000", ip)
    logger.info("")
    logger.info("🔧 SETUP INSTRUCTIONS FOR MOBILE APP:")
    logger.info("   1. Make sure your phone is on the same WiFi network")
    logger.info("   2. Open your mobile app")
    logger.info("   3. Try automatic scanning first")
    logger.info("   4. If scanning fails, manually enter: %s", primary_ip)
    logger.info("")
    logger.info("🔍 TROUBLESHOOTING:")
    logger.info("   • Check Windows Firewall (allow Python/SyncAnywhere)")
    logger.info("   • Verify both devices are on same WiFi")
    logger.info("   • Try each IP address listed above")
    logger.info("   • Check antivirus software settings")
    logger.info("")
    logger.info("📁 Logs are saved in the 'logs' folder")
    logger.info("🛑 Press Ctrl+C to stop the server")
    logger.info("=" * 80)

def create_connection_info_file():
    """Create a text file with connection info for easy reference"""
    try:
        all_ips = get_all_local_ips()
        primary_ip = get_best_local_ip()
        
        info_content = f"""SyncAnywhere Server Connection Information
====================================================

Primary IP Address: {primary_ip}:8000

All Available Connection URLs:
"""
        for ip in all_ips:
            info_content += f"  • http://{ip}:8000\n"
        
        info_content += f"""
Mobile App Setup:
1. Ensure your phone is connected to the same WiFi network
2. Open the mobile app
3. Use automatic scanning OR manually enter: {primary_ip}
4. Use password: IMC-MOBILE

Troubleshooting:
- Try each IP address listed above
- Check Windows Firewall settings
- Verify both devices are on the same WiFi
- Disable antivirus temporarily if needed

Server Status: http://{primary_ip}:8000/status

Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        with open("connection_info.txt", "w") as f:
            f.write(info_content)
        
        logging.info("📄 Connection info saved to: connection_info.txt")
        
    except Exception as e:
        logging.warning(f"⚠️ Could not create connection info file: {e}")

if __name__ == "__main__":
    logger = setup_startup_logging()
    
    logger.info("🚀 Starting SyncAnywhere System...")
    
    # Create connection info file
    create_connection_info_file()
    
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