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
        '%(asctime)s | %(levelname)-8s | %(message)s'
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
        '%(asctime)s | %(levelname)-8s | %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Log startup
    logging.info("=" * 60)
    logging.info("🚀 TELEMETRY API STARTING UP")
    logging.info("=" * 60)
    logging.info(f"📊 Log Level: {log_level}")
    logging.info(f"📁 Log File: {data_dir}/logs/app.log")
    logging.info(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("=" * 60)

def log_heartbeat():
    """Log system heartbeat with basic metrics"""
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        logging.info("💓 SYSTEM HEARTBEAT")
        logging.info(f"   CPU Usage: {cpu_percent:.1f}%")
        logging.info(f"   Memory: {memory.percent:.1f}% ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)")
        logging.info(f"   Disk: {disk.percent:.1f}% ({disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB)")
        logging.info("-" * 40)
    except ImportError:
        # Fallback without psutil
        logging.info("💓 HEARTBEAT - psutil not available")
        logging.info("-" * 40)

def log_request(method, path, status, duration_ms, client_ip, trace_id):
    """Log HTTP request in a readable format"""
    status_emoji = "✅" if status < 400 else "❌" if status >= 500 else "⚠️"
    duration_color = "🟢" if duration_ms < 100 else "🟡" if duration_ms < 500 else "🔴"
    
    logging.info(f"🌐 HTTP REQUEST")
    logging.info(f"   {status_emoji} {method} {path} → {status}")
    logging.info(f"   {duration_color} Duration: {duration_ms}ms")
    logging.info(f"   📍 Client: {client_ip}")
    logging.info(f"   🔍 Trace ID: {trace_id}")
    logging.info("-" * 40)

def log_ingest(records_count, success_count, failed_count, duration_ms):
    """Log ingest operation in a readable format"""
    success_rate = (success_count / records_count * 100) if records_count > 0 else 0
    status_emoji = "✅" if failed_count == 0 else "⚠️" if failed_count < records_count else "❌"
    
    logging.info(f"📥 INGEST OPERATION")
    logging.info(f"   {status_emoji} Records: {records_count} | Success: {success_count} | Failed: {failed_count}")
    logging.info(f"   📊 Success Rate: {success_rate:.1f}%")
    logging.info(f"   ⏱️  Duration: {duration_ms}ms")
    logging.info("-" * 40)

def log_system_event(event_type, message, details=None):
    """Log system events in a readable format"""
    emoji_map = {
        "startup": "🚀",
        "shutdown": "🛑", 
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "success": "✅"
    }
    
    emoji = emoji_map.get(event_type, "📝")
    logging.info(f"{emoji} SYSTEM EVENT: {message}")
    if details:
        logging.info(f"   📋 Details: {details}")
    logging.info("-" * 40)
