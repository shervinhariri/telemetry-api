import logging
import logging.config
import os
import yaml
import json
import threading
from datetime import datetime
from collections import deque
from typing import Dict, Any, Optional
import contextvars

# Context variable for trace ID
trace_id_var = contextvars.ContextVar('trace_id', default=None)

def get_trace_id() -> Optional[str]:
    """Get the current trace ID from context"""
    return trace_id_var.get()

def log_pipeline_event(event_type: str, message: str, **kwargs):
    """Log pipeline events with structured data"""
    logger = logging.getLogger("app")
    logger.info(message, extra={
        "event_type": event_type,
        "component": "pipeline",
        **kwargs
    })

class JsonFormatter(logging.Formatter):
    """Custom JSON formatter with structured fields"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Get trace ID from context
        trace_id = get_trace_id()
        
        # Build structured log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "trace_id": trace_id,
            "method": getattr(record, 'method', None),
            "path": getattr(record, 'path', None),
            "status": getattr(record, 'status', None),
            "latency_ms": getattr(record, 'latency_ms', None),
            "client_ip": getattr(record, 'client_ip', None),
            "tenant_id": getattr(record, 'tenant_id', None),
            "component": getattr(record, 'component', 'api')
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info', 'method', 'path', 'status', 
                          'latency_ms', 'client_ip', 'tenant_id', 'component']:
                log_entry[key] = value
        
        return json.dumps(log_entry)

class MemoryLogHandler(logging.Handler):
    """In-memory log handler with ring buffer for live logs"""
    
    def __init__(self, max_size: int = 10000):
        super().__init__()
        self.max_size = max_size
        self.logs = deque(maxlen=max_size)
        self._lock = threading.Lock()
    
    def emit(self, record: logging.LogRecord):
        try:
            # Format the record
            msg = self.format(record)
            
            # If using JSON formatter, parse the JSON
            if isinstance(self.formatter, JsonFormatter):
                try:
                    log_entry = json.loads(msg)
                except json.JSONDecodeError:
                    log_entry = {"msg": msg, "timestamp": datetime.utcnow().isoformat() + "Z"}
            else:
                # For text formatter, create structured entry
                log_entry = {
                    "msg": msg,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": record.levelname,
                    "logger": record.name
                }
            
            # Add to ring buffer
            with self._lock:
                self.logs.append(log_entry)
                
        except Exception:
            self.handleError(record)
    
    def get_logs(self, since: Optional[str] = None, limit: int = 1000) -> list:
        """Get logs from memory buffer with optional filtering"""
        with self._lock:
            logs = list(self.logs)
        
        # Filter by timestamp if provided
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                logs = [log for log in logs if log.get('timestamp') and 
                       datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')) >= since_dt]
            except ValueError:
                pass  # Invalid timestamp, return all logs
        
        # Apply limit
        return logs[-limit:] if limit else logs

# Global memory handler instance
memory_handler = MemoryLogHandler()

def setup_logging():
    """Setup logging configuration from YAML file or environment"""
    
    # Read environment overrides
    log_format = os.getenv("LOG_FORMAT", "json")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_sample_rate = float(os.getenv("LOG_SAMPLE_RATE", "1.0"))
    log_exclude_paths = os.getenv("LOG_EXCLUDE_PATHS", "/v1/health,/v1/metrics/prometheus").split(",")
    
    # Try to load YAML config
    config = None
    if os.path.exists("LOGGING.yaml"):
        try:
            with open("LOGGING.yaml", 'r') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: Could not load LOGGING.yaml: {e}")
    
    # Fallback to basic config if YAML not available
    if not config:
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {"()": JsonFormatter},
                "text": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": log_level,
                    "formatter": log_format,
                    "stream": "ext://sys.stdout"
                },
                "memory": {
                    "()": MemoryLogHandler,
                    "level": log_level,
                    "formatter": log_format,
                    "max_size": 10000
                }
            },
            "loggers": {
                "app": {
                    "level": log_level,
                    "handlers": ["console", "memory"],
                    "propagate": True
                },
                "uvicorn": {
                    "level": log_level,
                    "handlers": ["console", "memory"],
                    "propagate": True
                },
                "uvicorn.error": {
                    "level": log_level,
                    "handlers": ["console", "memory"],
                    "propagate": True
                },
                "uvicorn.access": {
                    "level": log_level,
                    "handlers": ["console", "memory"],
                    "propagate": True
                }
            },
            "root": {
                "level": log_level,
                "handlers": ["console", "memory"]
            }
        }
    
    # Apply environment overrides
    if log_format == "text":
        for handler in config.get("handlers", {}).values():
            if "formatter" in handler:
                handler["formatter"] = "text"
    
    # Apply log level override
    for logger in config.get("loggers", {}).values():
        logger["level"] = log_level
    
    # Configure logging
    logging.config.dictConfig(config)
    
    # Replace any existing memory handlers with our global instance
    loggers_to_update = [
        logging.getLogger(),  # root logger
        logging.getLogger("app"),
        logging.getLogger("uvicorn"),
        logging.getLogger("uvicorn.error"),
        logging.getLogger("uvicorn.access")
    ]
    
    # Get the formatter from the config
    formatter_name = log_format
    if formatter_name == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Set formatter on memory handler
    memory_handler.setFormatter(formatter)
    
    for logger in loggers_to_update:
        # Remove any existing memory handlers
        logger.handlers = [h for h in logger.handlers if not isinstance(h, MemoryLogHandler)]
        # Add our global memory handler
        logger.addHandler(memory_handler)
        logger.propagate = True  # Ensure logs propagate to parent loggers
    
    # Store configuration for middleware
    logging._config = {
        "exclude_paths": log_exclude_paths,
        "sample_rate": log_sample_rate
    }
    
    return config

def get_memory_handler():
    """Get the singleton memory handler instance"""
    return memory_handler

def get_memory_buffer():
    """Get the memory buffer for external access"""
    return memory_handler.logs
