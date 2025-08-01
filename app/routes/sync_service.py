# app/routes/sync_service.py
import time
import logging
import os
import sys
from datetime import datetime

def setup_service_logging():
    """Setup logging specifically for SyncService"""
    # Get the directory where the exe is running
    if getattr(sys, 'frozen', False):
        log_dir = os.path.dirname(sys.executable)
    else:
        log_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(log_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Setup logging with both file and console handlers
    log_file = os.path.join(log_dir, f"sync_service_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()  # This will show in console too
        ]
    )
    
    return logging.getLogger(__name__)

def run_sync_service():
    logger = setup_service_logging()
    
    logger.info("🚀 SyncService started successfully")
    logger.info("📁 Log files are being saved in the 'logs' folder")
    
    try:
        # Keep the service running indefinitely
        logger.info("🔄 SyncService is now running in background...")
        logger.info("ℹ️  Press Ctrl+C to stop the service")
        
        while True:
            # This keeps the service alive
            # You can add your sync logic here later
            logger.debug("🔧 SyncService heartbeat - running normally")
            time.sleep(30)  # Check every 30 seconds
            
    except KeyboardInterrupt:
        logger.info("🛑 SyncService stopped by user")
    except Exception as e:
        logger.error(f"❌ SyncService crashed: {str(e)}")
        logger.error("📋 Full error details:", exc_info=True)
    finally:
        logger.info("🔚 SyncService shutting down...")

if __name__ == "__main__":
    run_sync_service()