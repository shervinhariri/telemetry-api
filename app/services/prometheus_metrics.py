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
    ['status_class', 'path_group']
)

# HTTP admission decisions
HTTP_ADMITTED_TOTAL = Counter(
    'telemetry_http_admitted_total',
    'Total number of HTTP requests admitted by admission middleware'
)

HTTP_DROPPED_TOTAL = Counter(
    'telemetry_http_dropped_total',
    'Total number of HTTP requests dropped by admission middleware',
    ['reason']
)

# Request fitness buckets
REQUEST_FITNESS = Histogram(
    'telemetry_request_fitness',
    'Request fitness score distribution',
    buckets=[0.6, 0.9, 1.0]
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

# Blocked sources
BLOCKED_SOURCES_TOTAL = Counter(
    'telemetry_blocked_source_total',
    'Count of blocked events by admission control',
    ['source', 'reason']
)

# FIFO drops
FIFO_DROPPED_TOTAL = Counter(
    'telemetry_fifo_dropped_total',
    'Dropped events due to FIFO/backpressure'
)

# UDP packets received
UDP_PACKETS_RECEIVED_TOTAL = Counter(
    'telemetry_udp_packets_received_total',
    'Raw UDP packets accepted by collector'
)

# UDP admission decisions
UDP_ADMITTED_TOTAL = Counter(
    'telemetry_udp_admitted_total',
    'Total number of UDP packets admitted by UDP head'
)

UDP_DROPPED_TOTAL = Counter(
    'telemetry_udp_dropped_total',
    'Total number of UDP packets dropped by UDP head',
    ['reason']
)

# UDP head specific metrics
UDP_HEAD_READY = Gauge(
    'telemetry_udp_head_ready',
    'UDP head readiness status (1=ready, 0=not ready)'
)

UDP_HEAD_DATAGRAMS_TOTAL = Counter(
    'telemetry_udp_head_datagrams_total',
    'Total number of UDP datagrams received by UDP head'
)

UDP_HEAD_BIND_ERRORS_TOTAL = Counter(
    'telemetry_udp_head_bind_errors_total',
    'Total number of UDP head bind errors'
)

# P1: Additional UDP head metrics
UDP_HEAD_PACKETS_TOTAL = Counter(
    'telemetry_udp_head_packets_total',
    'Total number of UDP packets received by UDP head'
)

UDP_HEAD_BYTES_TOTAL = Counter(
    'telemetry_udp_head_bytes_total',
    'Total bytes received by UDP head'
)

UDP_HEAD_LAST_PACKET_TS = Gauge(
    'telemetry_udp_head_last_packet_ts',
    'Timestamp of last UDP packet received'
)

# Ingest metrics
INGEST_BATCHES_TOTAL = Counter(
    'telemetry_ingest_batches_total',
    'Total number of ingest batch requests'
)

INGEST_REJECT_TOTAL = Counter(
    'telemetry_ingest_reject_total',
    'Total number of ingest batch rejections',
    ['reason']
)

INGEST_BATCH_BYTES = Histogram(
    'telemetry_ingest_batch_bytes',
    'Compressed batch size in bytes',
    buckets=[1024, 10240, 102400, 512000, 1024000, 2097152, 4194304, 5242880]
)

INGEST_RECORDS_PER_BATCH = Histogram(
    'telemetry_ingest_records_per_batch',
    'Number of records per accepted batch',
    buckets=[1, 10, 50, 100, 500, 1000, 5000, 10000]
)

# Queue metrics
QUEUE_DEPTH = Gauge(
    'telemetry_queue_depth',
    'Current number of items in the processing queue'
)

QUEUE_SATURATION = Gauge(
    'telemetry_queue_saturation',
    'Queue saturation ratio (depth / max_depth)'
)

QUEUE_ENQUEUES_TOTAL = Counter(
    'telemetry_queue_enqueues_total',
    'Total number of records enqueued for processing'
)

QUEUE_DROPS_TOTAL = Counter(
    'telemetry_queue_drops_total',
    'Total number of records dropped due to queue full'
)

# Worker metrics
WORKER_PROCESSED_TOTAL = Counter(
    'telemetry_worker_processed_total',
    'Total number of records processed by workers'
)

WORKER_ERRORS_TOTAL = Counter(
    'telemetry_worker_errors_total',
    'Total number of worker processing errors',
    ['stage', 'kind']
)

# Processing latency metrics
EVENT_PROCESSING_SECONDS = Histogram(
    'telemetry_event_processing_seconds',
    'End-to-end event processing latency in seconds',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

STAGE_SECONDS = Histogram(
    'telemetry_stage_seconds',
    'Per-stage processing latency in seconds',
    ['stage'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

# HTTP IP allow-list blocks
HTTP_BLOCKED_IP_TOTAL = Counter(
    'telemetry_http_blocked_ip_total',
    'Total number of HTTP requests blocked by IP allow-list',
    ['source_id']
)

# Source type mismatches
SOURCE_TYPE_MISMATCH_TOTAL = Counter(
    'telemetry_source_type_mismatch_total',
    'Total number of source type mismatches (declared vs actual origin)',
    ['source_id']
)

# Export test counters
EXPORT_TEST_TOTAL = Counter(
    'telemetry_export_test_total',
    'Total number of export test attempts',
    ['dest', 'code']
)

# Output test counters (P1 T4)
OUTPUTS_TEST_SUCCESS_TOTAL = Counter(
    'telemetry_outputs_test_success_total',
    'Total number of successful output test attempts',
    ['target']
)

OUTPUTS_TEST_FAIL_TOTAL = Counter(
    'telemetry_outputs_test_fail_total',
    'Total number of failed output test attempts',
    ['target']
)

# Export operation counters
EXPORT_SENT_TOTAL = Counter(
    'telemetry_export_sent_total',
    'Total number of events successfully exported',
    ['dest']
)

# Enrichment metrics
GEOIP_LOADED = Gauge(
    'telemetry_geoip_loaded',
    'GeoIP database loaded status (1=loaded, 0=not loaded)'
)

GEOIP_LAST_REFRESH = Gauge(
    'telemetry_geoip_last_refresh_timestamp',
    'Timestamp of last GeoIP database refresh'
)

ASN_LOADED = Gauge(
    'telemetry_asn_loaded',
    'ASN database loaded status (1=loaded, 0=not loaded)'
)

ASN_LAST_REFRESH = Gauge(
    'telemetry_asn_last_refresh_timestamp',
    'Timestamp of last ASN database refresh'
)

THREATINTEL_LOADED = Gauge(
    'telemetry_threatintel_loaded',
    'Threat intelligence loaded status (1=loaded, 0=not loaded)'
)

THREATINTEL_SOURCES = Gauge(
    'telemetry_threatintel_sources',
    'Number of threat intelligence sources loaded'
)

THREATINTEL_MATCHES_TOTAL = Counter(
    'telemetry_threatintel_matches_total',
    'Total number of threat intelligence matches',
    ['type', 'source']
)

EXPORT_FAILED_TOTAL = Counter(
    'telemetry_export_failed_total',
    'Total number of export failures',
    ['dest', 'reason']
)

# Export latency histogram
EXPORT_LATENCY = Histogram(
    'telemetry_export_latency_ms',
    'Export latency in milliseconds',
    ['dest'],
    buckets=[10, 50, 100, 250, 500, 1000, 2500, 5000]
)

# Export backlog and DLQ gauges
EXPORT_BACKLOG = Gauge(
    'telemetry_export_backlog',
    'Number of events waiting to be exported',
    ['dest']
)

EXPORT_DLQ_DEPTH = Gauge(
    'telemetry_export_dlq_depth',
    'Number of failed events in DLQ',
    ['dest']
)

# Records parsed
RECORDS_PARSED_TOTAL = Counter(
    'telemetry_records_parsed_total',
    'Records successfully parsed and mapped'
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
PROCESSING_LATENCY = Histogram(
    'telemetry_processing_latency_ms',
    'Processing latency per record in milliseconds',
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
)

class PrometheusMetrics:
    """Service for managing Prometheus metrics."""
    
    def __init__(self):
        self._setup_build_info()
    
    def _setup_build_info(self):
        """Set up build information gauge."""
        version = os.getenv("APP_VERSION", os.getenv("TELEMETRY_VERSION", "0.8.11"))
        image = os.getenv("IMAGE", "shvin/telemetry-api")
        image_tag = os.getenv("IMAGE_TAG", "latest")
        
        BUILD_INFO.labels(
            version=version,
            image=image,
            image_tag=image_tag
        ).set(1)
    
    def increment_requests(self, status_code: int, path: str = "/unknown"):
        """Increment request counter."""
        # Categorize status codes
        if 200 <= status_code < 300:
            status_class = "2xx"
        elif 400 <= status_code < 500:
            status_class = "4xx"
        elif 500 <= status_code < 600:
            status_class = "5xx"
        else:
            status_class = "other"
        
        # Categorize paths
        if "/v1/ingest" in path:
            path_group = "ingest"
        elif "/v1/lookup" in path:
            path_group = "lookup"
        elif "/v1/outputs" in path:
            path_group = "outputs"
        elif "/v1/admin" in path:
            path_group = "admin"
        else:
            path_group = "other"
        
        REQUESTS_TOTAL.labels(status_class=status_class, path_group=path_group).inc()

    def increment_http_admitted(self, count: int = 1):
        HTTP_ADMITTED_TOTAL.inc(count)

    def increment_http_dropped(self, reason: str, count: int = 1):
        HTTP_DROPPED_TOTAL.labels(reason=reason).inc(count)
    
    def increment_http_blocked_ip(self, source_id: str, count: int = 1):
        """Increment HTTP blocked IP counter."""
        HTTP_BLOCKED_IP_TOTAL.labels(source_id=source_id).inc(count)
    
    def increment_source_type_mismatch(self, source_id: str, count: int = 1):
        """Increment source type mismatch counter."""
        SOURCE_TYPE_MISMATCH_TOTAL.labels(source_id=source_id).inc(count)
    
    def observe_request_fitness(self, fitness: float):
        """Observe request fitness score."""
        REQUEST_FITNESS.observe(fitness)
    
    def increment_records_processed(self, count: int = 1):
        """Increment records processed counter."""
        RECORDS_PROCESSED_TOTAL.inc(count)
    
    def increment_threat_matches(self, count: int = 1):
        """Increment threat matches counter."""
        THREAT_MATCHES_TOTAL.inc(count)
    
    def increment_blocked_source(self, source_id: str, reason: str):
        """Increment blocked source counter."""
        BLOCKED_SOURCES_TOTAL.labels(source=source_id, reason=reason).inc()
    
    def increment_fifo_dropped(self, count: int = 1):
        """Increment FIFO dropped counter."""
        FIFO_DROPPED_TOTAL.inc(count)
    
    def increment_udp_packets_received(self, count: int = 1):
        """Increment UDP packets received counter."""
        UDP_PACKETS_RECEIVED_TOTAL.inc(count)
    
    def increment_records_parsed(self, count: int = 1):
        """Increment records parsed counter."""
        RECORDS_PARSED_TOTAL.inc(count)

    def increment_udp_admitted(self, count: int = 1):
        """Increment UDP admitted counter."""
        UDP_ADMITTED_TOTAL.inc(count)

    def increment_udp_dropped(self, reason: str, count: int = 1):
        """Increment UDP dropped counter with reason."""
        UDP_DROPPED_TOTAL.labels(reason=reason).inc(count)

    def set_udp_head_ready(self, ready: bool):
        """Set UDP head readiness gauge."""
        UDP_HEAD_READY.set(1 if ready else 0)

    def increment_udp_head_datagrams(self, count: int = 1):
        """Increment UDP head datagrams counter."""
        UDP_HEAD_DATAGRAMS_TOTAL.inc(count)

    def increment_udp_head_bind_errors(self, count: int = 1):
        """Increment UDP head bind errors counter."""
        UDP_HEAD_BIND_ERRORS_TOTAL.inc(count)

    def increment_udp_head_packets(self, count: int = 1):
        """Increment UDP head packets counter."""
        UDP_HEAD_PACKETS_TOTAL.inc(count)

    def increment_udp_head_bytes(self, bytes_count: int):
        """Increment UDP head bytes counter."""
        UDP_HEAD_BYTES_TOTAL.inc(bytes_count)

    def set_udp_head_last_packet_ts(self, timestamp: float):
        """Set UDP head last packet timestamp."""
        UDP_HEAD_LAST_PACKET_TS.set(timestamp)

    def get_udp_head_packets_total(self) -> int:
        """Get UDP head packets total."""
        try:
            # Use the Prometheus client's sample method
            return int(next(UDP_HEAD_PACKETS_TOTAL._metrics.values())._value.get())
        except:
            return 0

    def get_udp_head_bytes_total(self) -> int:
        """Get UDP head bytes total."""
        try:
            # Use the Prometheus client's sample method
            return int(next(UDP_HEAD_BYTES_TOTAL._metrics.values())._value.get())
        except:
            return 0

    def get_udp_head_last_packet_ts(self) -> float:
        """Get UDP head last packet timestamp."""
        try:
            # Use the Prometheus client's sample method
            return float(next(UDP_HEAD_LAST_PACKET_TS._metrics.values())._value.get())
        except:
            return 0.0

    def increment_ingest_batches(self, count: int = 1):
        """Increment ingest batches counter."""
        INGEST_BATCHES_TOTAL.inc(count)

    def increment_ingest_reject(self, reason: str, count: int = 1):
        """Increment ingest reject counter with reason."""
        INGEST_REJECT_TOTAL.labels(reason=reason).inc(count)

    def observe_ingest_batch_bytes(self, bytes_count: int):
        """Observe ingest batch size in bytes."""
        INGEST_BATCH_BYTES.observe(bytes_count)

    def observe_ingest_records_per_batch(self, record_count: int):
        """Observe number of records per batch."""
        INGEST_RECORDS_PER_BATCH.observe(record_count)

    def set_queue_depth(self, depth: int):
        """Set queue depth gauge."""
        QUEUE_DEPTH.set(depth)

    def set_queue_saturation(self, saturation: float):
        """Set queue saturation gauge."""
        QUEUE_SATURATION.set(saturation)

    def increment_queue_enqueues(self, count: int = 1):
        """Increment queue enqueues counter."""
        QUEUE_ENQUEUES_TOTAL.inc(count)

    def increment_queue_drops(self, count: int = 1):
        """Increment queue drops counter."""
        QUEUE_DROPS_TOTAL.inc(count)

    def increment_worker_processed(self, count: int = 1):
        """Increment worker processed counter."""
        WORKER_PROCESSED_TOTAL.inc(count)

    def increment_worker_errors(self, stage: str, kind: str, count: int = 1):
        """Increment worker errors counter with stage and kind."""
        WORKER_ERRORS_TOTAL.labels(stage=stage, kind=kind).inc(count)

    def observe_event_processing_seconds(self, seconds: float):
        """Observe event processing latency."""
        EVENT_PROCESSING_SECONDS.observe(seconds)

    def observe_stage_seconds(self, stage: str, seconds: float):
        """Observe stage processing latency."""
        STAGE_SECONDS.labels(stage=stage).observe(seconds)

    def increment_export_test(self, dest: str, code: str):
        """Increment export test counter."""
        EXPORT_TEST_TOTAL.labels(dest=dest, code=code).inc()

    def increment_outputs_test_success(self, target: str):
        """Increment successful output test counter."""
        OUTPUTS_TEST_SUCCESS_TOTAL.labels(target=target).inc()

    def increment_outputs_test_fail(self, target: str):
        """Increment failed output test counter."""
        OUTPUTS_TEST_FAIL_TOTAL.labels(target=target).inc()

    def increment_export_sent(self, dest: str, count: int = 1):
        """Increment export sent counter."""
        EXPORT_SENT_TOTAL.labels(dest=dest).inc(count)

    def increment_export_failed(self, dest: str, reason: str, count: int = 1):
        """Increment export failed counter."""
        EXPORT_FAILED_TOTAL.labels(dest=dest, reason=reason).inc(count)

    def observe_export_latency(self, dest: str, latency_ms: float):
        """Observe export latency."""
        EXPORT_LATENCY.labels(dest=dest).observe(latency_ms)

    def set_export_backlog(self, dest: str, count: int):
        """Set export backlog gauge."""
        EXPORT_BACKLOG.labels(dest=dest).set(count)

    def set_export_dlq_depth(self, dest: str, count: int):
        """Set export DLQ depth gauge."""
        EXPORT_DLQ_DEPTH.labels(dest=dest).set(count)
    
    def set_eps(self, eps: float):
        """Set events per second gauge."""
        EPS.set(eps)
    
    def set_queue_lag(self, lag_ms: float):
        """Set queue lag gauge."""
        QUEUE_LAG.set(lag_ms)
    
    def observe_processing_latency(self, latency_ms: float):
        """Observe processing latency."""
        PROCESSING_LATENCY.observe(latency_ms)
    
    # Enrichment metrics
    def set_geoip_loaded(self, loaded: bool):
        """Set GeoIP loaded status."""
        GEOIP_LOADED.set(1 if loaded else 0)
    
    def set_geoip_last_refresh(self, timestamp: float):
        """Set GeoIP last refresh timestamp."""
        GEOIP_LAST_REFRESH.set(timestamp)
    
    def set_asn_loaded(self, loaded: bool):
        """Set ASN loaded status."""
        ASN_LOADED.set(1 if loaded else 0)
    
    def set_asn_last_refresh(self, timestamp: float):
        """Set ASN last refresh timestamp."""
        ASN_LAST_REFRESH.set(timestamp)
    
    def set_threatintel_loaded(self, loaded: bool):
        """Set threat intelligence loaded status."""
        THREATINTEL_LOADED.set(1 if loaded else 0)
    
    def set_threatintel_sources(self, count: int):
        """Set number of threat intelligence sources."""
        THREATINTEL_SOURCES.set(count)
    
    def increment_threatintel_matches(self, match_type: str, source: str, count: int = 1):
        """Increment threat intelligence matches counter."""
        THREATINTEL_MATCHES_TOTAL.labels(type=match_type, source=source).inc(count)
    
    def get_metrics(self) -> bytes:
        """Get Prometheus metrics in text format."""
        return generate_latest()
    
    def get_content_type(self) -> str:
        """Get the content type for Prometheus metrics."""
        return CONTENT_TYPE_LATEST

# Global metrics instance
prometheus_metrics = PrometheusMetrics()
