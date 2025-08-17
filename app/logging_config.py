import logging
import logging.handlers
import os
import json
import time
import threading
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from queue import Queue
import asyncio

# Global configuration
LOG_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO").upper(),
    "format": os.getenv("LOG_FORMAT", "json").lower(),
    "http_enabled": os.getenv("HTTP_LOG_ENABLED", "true").lower() == "true",
    "http_sample_rate": float(os.getenv("HTTP_LOG_SAMPLE_RATE", "0.01")),
    "http_exclude_paths": set(os.getenv("HTTP_LOG_EXCLUDE_PATHS", "/v1/metrics,/v1/system,/v1/logs/tail,/v1/admin/requests").split(",")),
    "redact_headers": set(os.getenv("REDACT_HEADERS", "authorization,x-api-key").split(",")),
    "is_dev": os.getenv("ENVIRONMENT", "production").lower() == "development"
}

# Global log queue for async logging
log_queue = Queue(maxsize=10000)
log_listener = None

class StructuredFormatter:
    """JSON formatter for structured logging"""
    
    def __init__(self, is_dev: bool = False):
        self.is_dev = is_dev
    
    def format(self, record: logging.LogRecord) -> str:
        # Base structured log entry
        log_entry = {
            "ts": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'trace_id'):
            log_entry['trace_id'] = record.trace_id
        if hasattr(record, 'client_ip'):
            log_entry['client_ip'] = record.client_ip
        if hasattr(record, 'tenant_id'):
            log_entry['tenant_id'] = record.tenant_id
        if hasattr(record, 'method'):
            log_entry['method'] = record.method
        if hasattr(record, 'path'):
            log_entry['path'] = record.path
        if hasattr(record, 'status'):
            log_entry['status'] = record.status
        if hasattr(record, 'latency_ms'):
            log_entry['latency_ms'] = record.latency_ms
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Development mode: pretty print with emojis
        if self.is_dev:
            return self._format_dev(log_entry)
        
        # Production mode: compact JSON
        return json.dumps(log_entry, separators=(',', ':'))
    
    def _format_dev(self, log_entry: Dict[str, Any]) -> str:
        """Development-friendly formatting with emojis"""
        emoji_map = {
            "INFO": "ℹ️",
            "WARNING": "⚠️", 
            "ERROR": "❌",
            "CRITICAL": "🚨",
            "DEBUG": "🐛"
        }
        
        emoji = emoji_map.get(log_entry["level"], "📝")
        timestamp = log_entry["ts"]
        level = log_entry["level"]
        message = log_entry["msg"]
        
        # Build dev-friendly log line
        parts = [f"{timestamp} | {emoji} {level:8} | {message}"]
        
        # Add extra context if present
        if 'trace_id' in log_entry:
            parts.append(f"🔍 Trace: {log_entry['trace_id']}")
        if 'client_ip' in log_entry:
            parts.append(f"📍 Client: {log_entry['client_ip']}")
        if 'method' in log_entry and 'path' in log_entry:
            parts.append(f"🌐 {log_entry['method']} {log_entry['path']}")
        if 'status' in log_entry:
            status_emoji = "✅" if log_entry['status'] < 400 else "❌" if log_entry['status'] >= 500 else "⚠️"
            parts.append(f"{status_emoji} Status: {log_entry['status']}")
        if 'latency_ms' in log_entry:
            latency_color = "🟢" if log_entry['latency_ms'] < 100 else "🟡" if log_entry['latency_ms'] < 500 else "🔴"
            parts.append(f"{latency_color} Latency: {log_entry['latency_ms']}ms")
        
        return " | ".join(parts)
    
    def formatException(self, exc_info):
        """Format exception information"""
        import traceback
        return ''.join(traceback.format_exception(*exc_info))

class QueueHandler(logging.Handler):
    """Non-blocking queue handler for async logging"""
    
    def __init__(self, queue: Queue):
        super().__init__()
        self.queue = queue
    
    def emit(self, record):
        try:
            # Don't block if queue is full
            self.queue.put_nowait(record)
        except:
            # Fallback to stderr if queue is full
            import sys
            print(f"Log queue full, dropping log: {record.getMessage()}", file=sys.stderr)

class QueueListener(threading.Thread):
    """Background thread to process log queue"""
    
    def __init__(self, queue: Queue, handler: logging.Handler):
        super().__init__(daemon=True)
        self.queue = queue
        self.handler = handler
        self.running = True
    
    def run(self):
        while self.running:
            try:
                record = self.queue.get(timeout=1)
                self.handler.handle(record)
            except:
                continue
    
    def stop(self):
        self.running = False

def setup_logging():
    """Configure structured logging with queue-based async processing"""
    global log_listener
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, LOG_CONFIG["level"]))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = StructuredFormatter(is_dev=LOG_CONFIG["is_dev"])
    
    # Create stdout handler (for Docker/Kubernetes log collection)
    stdout_handler = logging.StreamHandler()
    stdout_handler.setFormatter(formatter)
    
    # Create queue handler for async processing
    queue_handler = QueueHandler(log_queue)
    queue_handler.setFormatter(formatter)
    
    # Start background listener
    log_listener = QueueListener(log_queue, stdout_handler)
    log_listener.start()
    
    # Add queue handler to root logger
    logger.addHandler(queue_handler)
    
    # Log startup
    startup_logger = logging.getLogger("startup")
    startup_logger.info("🚀 TELEMETRY API STARTING UP", extra={
        "trace_id": "startup"
    })
    startup_logger.info(f"📊 Log Configuration", extra={
        "trace_id": "startup",
        "level": LOG_CONFIG["level"],
        "format": LOG_CONFIG["format"],
        "http_enabled": LOG_CONFIG["http_enabled"],
        "http_sample_rate": LOG_CONFIG["http_sample_rate"],
        "is_dev": LOG_CONFIG["is_dev"]
    })

def should_log_request(method: str, path: str, status: int) -> bool:
    """Determine if HTTP request should be logged based on sampling and filtering rules"""
    # Always log errors
    if status >= 400:
        return True
    
    # Skip excluded paths
    if path in LOG_CONFIG["http_exclude_paths"]:
        return False
    
    # Sample successful requests
    if status < 400:
        return random.random() < LOG_CONFIG["http_sample_rate"]
    
    return True

def log_http_request(method: str, path: str, status: int, duration_ms: int, 
                    client_ip: str, trace_id: str, tenant_id: str = "unknown"):
    """Log HTTP request with structured data"""
    if not LOG_CONFIG["http_enabled"]:
        return
    
    if not should_log_request(method, path, status):
        return
    
    logger = logging.getLogger("http")
    logger.info("HTTP Request", extra={
        "trace_id": trace_id,
        "client_ip": client_ip,
        "tenant_id": tenant_id,
        "method": method,
        "path": path,
        "status": status,
        "latency_ms": duration_ms
    })

# Alias for backward compatibility
log_request = log_http_request

def log_system_event(event_type: str, message: str, details: Optional[Dict[str, Any]] = None, 
                    trace_id: str = "system"):
    """Log system events with structured data"""
    logger = logging.getLogger("system")
    
    extra = {
        "trace_id": trace_id,
        "event_type": event_type
    }
    
    if details:
        extra.update(details)
    
    logger.info(message, extra=extra)

def log_ingest_operation(records_count: int, success_count: int, failed_count: int, 
                        duration_ms: int, trace_id: str):
    """Log ingest operations with structured data"""
    logger = logging.getLogger("ingest")
    
    success_rate = (success_count / records_count * 100) if records_count > 0 else 0
    
    logger.info("Ingest Operation", extra={
        "trace_id": trace_id,
        "records_count": records_count,
        "success_count": success_count,
        "failed_count": failed_count,
        "success_rate": round(success_rate, 1),
        "duration_ms": duration_ms
    })

def log_pipeline_event(event_type: str, message: str, **kwargs):
    """Log pipeline events with structured data"""
    logger = logging.getLogger("pipeline")
    
    extra = {
        "event_type": event_type
    }
    extra.update(kwargs)
    
    logger.info(message, extra=extra)

def redact_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive information from log data"""
    redacted = data.copy()
    
    for header in LOG_CONFIG["redact_headers"]:
        if header in redacted:
            redacted[header] = "[REDACTED]"
    
    return redacted

def cleanup_logging():
    """Cleanup logging resources"""
    global log_listener
    if log_listener:
        log_listener.stop()
        log_listener.join(timeout=5)
