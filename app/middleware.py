import time
import uuid
from typing import Callable, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
from collections import deque
from .logging_config import get_trace_id, trace_id_var

# Global requests store
requests_store = deque(maxlen=1000)

logger = logging.getLogger("app")

class TracingMiddleware(BaseHTTPMiddleware):
    """ASGI middleware for request tracing and structured logging"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.log_config = getattr(logging, '_config', {
            "exclude_paths": ["/v1/health", "/v1/metrics/prometheus"],
            "sample_rate": 1.0
        })
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or reuse trace ID
        trace_id = request.headers.get("X-Request-ID")
        if not trace_id:
            trace_id = str(uuid.uuid4())
        
        # Set trace ID in context
        trace_id_var.set(trace_id)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Get tenant ID from headers
        tenant_id = request.headers.get("X-Tenant-ID", "unknown")
        
        # Start timing
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate latency
            latency_ms = round((time.time() - start_time) * 1000, 2)
            
            # Store request record (always store, regardless of logging)
            request_record = {
                "ts": time.time(),
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": latency_ms,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_ip": client_ip
            }
            requests_store.append(request_record)
            
            # Log request (with sampling)
            self._log_request(
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                latency_ms=latency_ms,
                client_ip=client_ip,
                tenant_id=tenant_id,
                trace_id=trace_id
            )
            
            # Record metrics
            from .metrics import increment_requests
            increment_requests(failed=False, latency_ms=latency_ms)
            
            # Add trace ID to response headers
            response.headers["X-Request-ID"] = trace_id
            
            return response
            
        except Exception as e:
            # Calculate latency for failed requests
            latency_ms = round((time.time() - start_time) * 1000, 2)
            
            # Log error
            logger.error(f"Request failed: {str(e)}", extra={
                "method": request.method,
                "path": request.url.path,
                "status": 500,
                "latency_ms": latency_ms,
                "client_ip": client_ip,
                "tenant_id": tenant_id,
                "trace_id": trace_id,
                "exception": str(e)
            })
            
            # Record failed request metrics
            from .metrics import increment_requests
            increment_requests(failed=True, latency_ms=latency_ms)
            
            # Re-raise the exception
            raise
        finally:
            # Clear trace ID from context
            trace_id_var.set(None)
    
    def _log_request(self, method: str, path: str, status: int, latency_ms: float,
                    client_ip: str, tenant_id: str, trace_id: str):
        """Log HTTP request with structured data and sampling"""
        
        # Skip excluded paths
        if path in self.log_config["exclude_paths"]:
            return
        
        # Always log errors
        if status >= 400:
            log_level = logging.ERROR if status >= 500 else logging.WARNING
            logger.log(log_level, "HTTP Request", extra={
                "method": method,
                "path": path,
                "status": status,
                "latency_ms": latency_ms,
                "client_ip": client_ip,
                "tenant_id": tenant_id,
                "trace_id": trace_id
            })
            return
        
        # Sample successful requests
        import random
        if random.random() > self.log_config["sample_rate"]:
            return
        
        # Log successful request
        logger.info("HTTP Request", extra={
            "method": method,
            "path": path,
            "status": status,
            "latency_ms": latency_ms,
            "client_ip": client_ip,
            "tenant_id": tenant_id,
            "trace_id": trace_id
        })

def get_requests_store():
    """Get the requests store for external access"""
    return requests_store
