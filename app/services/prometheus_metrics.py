"""
Prometheus metrics for Telemetry API
"""

from prometheus_client import Counter, Gauge, Histogram, Summary, generate_latest, CONTENT_TYPE_LATEST
from typing import Dict, Any
import time
import os

# Build info
BUILD_INFO = Gauge(
    'build_info',
    'Build information',
    ['version', 'image', 'image_tag']
)

# Request counters
REQUESTS_TOTAL = Counter(
    'telemetry_requests_total',
    'Total number of requests',
    ['code', 'tenant']
)

# Records processed
RECORDS_PROCESSED_TOTAL = Counter(
    'telemetry_records_processed_total',
    'Total number of records processed'
)

# Threat matches
THREAT_MATCHES_TOTAL = Counter(
    'telemetry_threat_matches_total',
    'Total number of threat matches'
)

# Events per second (gauge)
EPS = Gauge(
    'telemetry_eps',
    'Events per second (60s rolling average)'
)

# Queue lag
QUEUE_LAG = Gauge(
    'telemetry_queue_lag',
    'Queue lag in milliseconds'
)

# Processing latency
PROCESSING_LATENCY = Summary(
    'telemetry_processing_latency_ms',
    'Processing latency in milliseconds'
)

class PrometheusMetrics:
    """Service for managing Prometheus metrics."""
    
    def __init__(self):
        self._setup_build_info()
    
    def _setup_build_info(self):
        """Set up build information gauge."""
        version = os.getenv("APP_VERSION", "0.7.9")
        image = os.getenv("IMAGE", "shvin/telemetry-api")
        image_tag = os.getenv("IMAGE_TAG", "latest")
        
        BUILD_INFO.labels(
            version=version,
            image=image,
            image_tag=image_tag
        ).set(1)
    
    def increment_requests(self, status_code: int, tenant: str = "default"):
        """Increment request counter."""
        # Categorize status codes
        if 200 <= status_code < 300:
            code = "2xx"
        elif 400 <= status_code < 500:
            code = "4xx"
        elif 500 <= status_code < 600:
            code = "5xx"
        else:
            code = "other"
        
        REQUESTS_TOTAL.labels(code=code, tenant=tenant).inc()
    
    def increment_records_processed(self, count: int = 1):
        """Increment records processed counter."""
        RECORDS_PROCESSED_TOTAL.inc(count)
    
    def increment_threat_matches(self, count: int = 1):
        """Increment threat matches counter."""
        THREAT_MATCHES_TOTAL.inc(count)
    
    def set_eps(self, eps: float):
        """Set events per second gauge."""
        EPS.set(eps)
    
    def set_queue_lag(self, lag_ms: float):
        """Set queue lag gauge."""
        QUEUE_LAG.set(lag_ms)
    
    def observe_processing_latency(self, latency_ms: float):
        """Observe processing latency."""
        PROCESSING_LATENCY.observe(latency_ms)
    
    def get_metrics(self) -> bytes:
        """Get Prometheus metrics in text format."""
        return generate_latest()
    
    def get_content_type(self) -> str:
        """Get the content type for Prometheus metrics."""
        return CONTENT_TYPE_LATEST

# Global metrics instance
prometheus_metrics = PrometheusMetrics()
