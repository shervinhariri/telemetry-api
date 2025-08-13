import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime

def setup_logging():
    """Configure logging with rotating file handler"""
    # Create data directory
    data_dir = Path("/data")
    data_dir.mkdir(exist_ok=True)
    (data_dir / "logs").mkdir(exist_ok=True)
    
    # Get log level from environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        data_dir / "logs" / "app.log",
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Log startup
    logging.info(f"Logging configured - level: {log_level}, file: {data_dir}/logs/app.log")

def log_heartbeat():
    """Log system heartbeat with basic metrics"""
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        logging.info(
            f"HEARTBEAT - CPU: {cpu_percent:.1f}%, "
            f"Memory: {memory.percent:.1f}%, "
            f"Disk: {disk.percent:.1f}%"
        )
    except ImportError:
        # Fallback without psutil
        logging.info("HEARTBEAT - psutil not available")
