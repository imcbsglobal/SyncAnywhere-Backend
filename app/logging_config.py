# app/logging_config.py

import logging
from logging.config import dictConfig
import os
import sys
from datetime import datetime

def setup_logging():
    """Setup comprehensive logging for the main application"""
    
    # Get the directory where the exe is running
    if getattr(sys, 'frozen', False):
        log_dir = os.path.dirname(sys.executable)
    else:
        log_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Create logs directory
    log_dir = os.path.join(log_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate log file names with date
    today = datetime.now().strftime('%Y%m%d')
    app_log_file = os.path.join(log_dir, f"syncanywhere_{today}.log")
    error_log_file = os.path.join(log_dir, f"errors_{today}.log")
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "simple": {
                "format": "%(asctime)s - %(levelname)s - %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "simple",
                "level": "INFO",
            },
            "app_file": {
                "class": "logging.FileHandler",
                "formatter": "detailed",
                "filename": app_log_file,
                "encoding": "utf-8",
                "level": "DEBUG",
            },
            "error_file": {
                "class": "logging.FileHandler",
                "formatter": "detailed",
                "filename": error_log_file,
                "encoding": "utf-8",
                "level": "ERROR",
            },
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["console", "app_file", "error_file"],
        },
        "loggers": {
            "uvicorn": {
                "level": "INFO",
                "handlers": ["app_file"],
                "propagate": False,
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["app_file", "error_file"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["app_file"],
                "propagate": False,
            },
        },
    }

    dictConfig(logging_config)
    
    # Log the setup completion
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("🚀 SyncAnywhere Application Started")
    logger.info(f"📁 Logs are being saved to: {log_dir}")
    logger.info(f"📝 Main log file: {app_log_file}")
    logger.info(f"🚨 Error log file: {error_log_file}")
    logger.info("=" * 50)