import time
import threading
from collections import deque
from typing import Dict, Any, List, Optional
import statistics
from .services.prometheus_metrics import prometheus_metrics

class MetricsAggregator:
    def __init__(self):
        self.lock = threading.Lock()
        
        # Counters (since start)
        self.totals = {
            "events": 0,
            "batches": 0,
            "threat_matches": 0,
            "unique_sources": set(),
            "risk_sum": 0,
            "risk_count": 0,
            "blocked_sources": 0
        }
        
        # Request counters
        self.requests_total = 0
        self.requests_failed = 0
        self.requests_success = 0
        self.latency_samples = deque(maxlen=1000)  # For latency statistics
        
        # Blocked source counters by reason
        self.blocked_sources = {
            "disabled": 0,
            "ip_not_allowed": 0,
            "rate_limit": 0
        }
        
        # Sliding windows (5 minutes @ 1s resolution)
        self.window_size = 300  # 5 minutes
        self.eps_window = deque(maxlen=self.window_size)  # events per second
        self.bpm_window = deque(maxlen=self.window_size)  # batches per minute (accumulated)
        self.threats_window = deque(maxlen=self.window_size)  # threat matches per second
        self.risk_window = deque(maxlen=self.window_size)  # latest risk scores
        
        # Queue lag tracking
        self.lag_samples = deque(maxlen=1000)  # reservoir for quantiles
        
        # Time series data (last 5 minutes)
        self.timeseries = {
            "eps": [],
            "bpm": [],
            "threats": [],
            "avg_risk": []
        }
        
        # Current minute accumulator for bpm
        self.current_minute_batches = 0
        self.last_minute_tick = int(time.time() // 60)
        
        # Background tick task
        self.last_tick = time.time()
        
        # Admission counters (HTTP and UDP)
        self.http_admitted_total = 0
        self.http_dropped_total = {}
        self.udp_admitted_total = 0
        self.udp_dropped_total = {}
        
        # Export counters
        self.export_sent_total = {"splunk": 0, "elastic": 0}
        self.export_failed_total = {"splunk": {}, "elastic": {}}
        self.export_test_total = {"splunk": 0, "elastic": 0}
        
        # P1 T4: Output test counters
        self.outputs_test_success_total = {"splunk": 0, "elastic": 0}
        self.outputs_test_fail_total = {"splunk": 0, "elastic": 0}
        
        # Per-source counters and ring buffers
        self.source_admitted_total = {}  # source_id -> count
        self.source_dropped_total = {}   # source_id -> {reason -> count}
        self.source_eps_buffers = {}     # source_id -> ring buffer of 60 buckets
        self.source_error_buffers = {}   # source_id -> ring buffer of 60 buckets

    def increment_requests(self, failed: bool = False, latency_ms: float = None):
        """Increment request counters"""
        with self.lock:
            self.requests_total += 1
            if failed:
                self.requests_failed += 1
            else:
                self.requests_success += 1
            
            # Record latency if provided
            if latency_ms is not None:
                self.latency_samples.append(latency_ms)
            
            # Update Prometheus metrics
            status_code = 500 if failed else 200
            prometheus_metrics.increment_requests(status_code)
    
    def record_blocked_source(self, source_id: str, reason: str):
        """Record a blocked source admission"""
        with self.lock:
            self.totals["blocked_sources"] += 1
            if reason in self.blocked_sources:
                self.blocked_sources[reason] += 1
            
            # Update Prometheus metrics
            prometheus_metrics.increment_blocked_source(source_id, reason)
                
    def record_batch(self, record_count: int, threat_matches: int, risk_scores: List[int], sources: List[str]):
        """Record a processed batch"""
        with self.lock:
            # Update totals
            self.totals["events"] += record_count
            self.totals["batches"] += 1
            self.totals["threat_matches"] += threat_matches
            self.totals["risk_sum"] += sum(risk_scores)
            self.totals["risk_count"] += len(risk_scores)
            
            # Update unique sources
            for source in sources:
                if source:
                    self.totals["unique_sources"].add(source)
                    
            # Update current minute batch counter
            self.current_minute_batches += 1
            
            # Update Prometheus metrics
            prometheus_metrics.increment_records_processed(record_count)
            if threat_matches > 0:
                prometheus_metrics.increment_threat_matches(threat_matches)
            
    def record_queue_lag(self, lag_ms: int):
        """Record queue lag measurement"""
        with self.lock:
            self.lag_samples.append(lag_ms)
            
        # Update Prometheus metrics
        prometheus_metrics.set_queue_lag(lag_ms)

    # ----- Admission accounting -----
    def record_http_admitted(self, count: int = 1):
        with self.lock:
            self.http_admitted_total += count
        # Prometheus
        prometheus_metrics.increment_http_admitted(count)

    def record_http_dropped(self, reason: str, count: int = 1):
        with self.lock:
            self.http_dropped_total[reason] = self.http_dropped_total.get(reason, 0) + count
        # Prometheus
        prometheus_metrics.increment_http_dropped(reason, count)

    def record_udp_admitted(self, count: int = 1):
        with self.lock:
            self.udp_admitted_total += count
        # Prometheus
        prometheus_metrics.increment_udp_admitted(count)

    def record_udp_dropped(self, reason: str, count: int = 1):
        with self.lock:
            self.udp_dropped_total[reason] = self.udp_dropped_total.get(reason, 0) + count
        # Prometheus
        prometheus_metrics.increment_udp_dropped(reason, count)

    # ----- Export accounting -----
    def record_export_sent(self, dest: str, count: int = 1):
        with self.lock:
            self.export_sent_total[dest] = self.export_sent_total.get(dest, 0) + count
        # Prometheus
        prometheus_metrics.increment_export_sent(dest, count)

    def record_export_failed(self, dest: str, reason: str, count: int = 1):
        with self.lock:
            if dest not in self.export_failed_total:
                self.export_failed_total[dest] = {}
            self.export_failed_total[dest][reason] = self.export_failed_total[dest].get(reason, 0) + count
        # Prometheus
        prometheus_metrics.increment_export_failed(dest, reason, count)

    def record_export_test(self, dest: str, count: int = 1):
        with self.lock:
            self.export_test_total[dest] = self.export_test_total.get(dest, 0) + count
    
    def record_outputs_test_success(self, target: str):
        """Record successful output test"""
        with self.lock:
            self.outputs_test_success_total[target] = self.outputs_test_success_total.get(target, 0) + 1
            prometheus_metrics.increment_outputs_test_success(target)
    
    def record_outputs_test_fail(self, target: str):
        """Record failed output test"""
        with self.lock:
            self.outputs_test_fail_total[target] = self.outputs_test_fail_total.get(target, 0) + 1
            prometheus_metrics.increment_outputs_test_fail(target)
            
    # ----- Per-source accounting -----
    def record_source_admitted(self, source_id: str, count: int = 1):
        with self.lock:
            self.source_admitted_total[source_id] = self.source_admitted_total.get(source_id, 0) + count
        # Prometheus
        prometheus_metrics.increment_http_admitted()  # Reuse existing counter for now

    def record_source_dropped(self, source_id: str, reason: str, count: int = 1):
        with self.lock:
            if source_id not in self.source_dropped_total:
                self.source_dropped_total[source_id] = {}
            self.source_dropped_total[source_id][reason] = self.source_dropped_total[source_id].get(reason, 0) + count
        # Prometheus
        prometheus_metrics.increment_http_dropped(reason)

    def update_source_eps(self, source_id: str, eps: float):
        """Update source EPS ring buffer"""
        with self.lock:
            if source_id not in self.source_eps_buffers:
                self.source_eps_buffers[source_id] = []
            self.source_eps_buffers[source_id].append(eps)
            # Keep only last 60 buckets
            if len(self.source_eps_buffers[source_id]) > 60:
                self.source_eps_buffers[source_id] = self.source_eps_buffers[source_id][-60:]

    def update_source_error_pct(self, source_id: str, error_pct: float):
        """Update source error percentage ring buffer"""
        with self.lock:
            if source_id not in self.source_error_buffers:
                self.source_error_buffers[source_id] = []
            self.source_error_buffers[source_id].append(error_pct)
            # Keep only last 60 buckets
            if len(self.source_error_buffers[source_id]) > 60:
                self.source_error_buffers[source_id] = self.source_error_buffers[source_id][-60:]

    def get_source_eps_1m(self, source_id: str) -> float:
        """Get 1-minute average EPS for source"""
        with self.lock:
            if source_id not in self.source_eps_buffers or not self.source_eps_buffers[source_id]:
                return 0.0
            return sum(self.source_eps_buffers[source_id]) / len(self.source_eps_buffers[source_id])

    def get_source_error_pct_1m(self, source_id: str) -> float:
        """Get 1-minute average error percentage for source"""
        with self.lock:
            if source_id not in self.source_error_buffers or not self.source_error_buffers[source_id]:
                return 0.0
            return sum(self.source_error_buffers[source_id]) / len(self.source_error_buffers[source_id])
    
    def _get_udp_head_metrics(self) -> Dict[str, Any]:
        """Get UDP head metrics"""
        try:
            from .udp_head import get_udp_stats
            stats = get_udp_stats()
            return {
                "ready": stats["ready"],
                "bind_errors": stats["bind_errors"],
                "datagrams_total": stats["datagrams_total"],
                "packets_total": stats["packets_total"],
                "bytes_total": stats["bytes_total"],
                "last_packet_ts": stats["last_packet_ts"],
                "port": stats["port"]
            }
        except Exception:
            return {
                "ready": False,
                "bind_errors": 0,
                "datagrams_total": 0,
                "packets_total": 0,
                "bytes_total": 0,
                "last_packet_ts": 0.0,
                "port": None
            }
            
    def tick(self):
        """Background tick to roll windows and update time series"""
        now = time.time()
        current_second = int(now)
        
        with self.lock:
            # Roll minute counter if needed
            current_minute = int(now // 60)
            if current_minute > self.last_minute_tick:
                # Add accumulated batches to window
                self.bpm_window.append(self.current_minute_batches)
                self.current_minute_batches = 0
                self.last_minute_tick = current_minute
                
            # Update time series every 5 seconds
            if current_second % 5 == 0:
                self._update_timeseries(now)
                
    def _update_timeseries(self, now: float):
        """Update time series data"""
        ts_ms = int(now * 1000)
        
        # Calculate current rates from windows
        eps = len(self.eps_window) if self.eps_window else 0
        bpm = sum(self.bpm_window) if self.bpm_window else 0
        threats = len(self.threats_window) if self.threats_window else 0
        
        # Calculate average risk from recent samples
        avg_risk = 0
        if self.risk_window:
            avg_risk = sum(self.risk_window) / len(self.risk_window)
            
        # Add to time series (keep last 60 points = 5 minutes)
        self.timeseries["eps"].append([ts_ms, eps])
        self.timeseries["bpm"].append([ts_ms, bpm])
        self.timeseries["threats"].append([ts_ms, threats])
        self.timeseries["avg_risk"].append([ts_ms, avg_risk])
        
        # Keep only last 60 points
        for key in self.timeseries:
            if len(self.timeseries[key]) > 60:
                self.timeseries[key] = self.timeseries[key][-60:]
        
        # Update Prometheus EPS gauge
        prometheus_metrics.set_eps(eps)
                
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        with self.lock:
            # Calculate current rates
            eps_1m = len(self.eps_window) if self.eps_window else 0
            epm_1m = eps_1m * 60  # events per minute
            bpm_1m = sum(self.bpm_window) if self.bpm_window else 0
            
            # Calculate queue lag percentiles
            lag_p50 = lag_p95 = lag_p99 = 0
            if self.lag_samples:
                sorted_lag = sorted(self.lag_samples)
                lag_p50 = sorted_lag[len(sorted_lag) // 2]
                lag_p95 = sorted_lag[int(len(sorted_lag) * 0.95)]
                lag_p99 = sorted_lag[int(len(sorted_lag) * 0.99)]
                
            return {
                "requests_total": self.requests_total,
                "requests_failed": self.requests_failed,
                "requests_success": self.requests_success,
                "requests_last_15m_success_rate": self._calculate_success_rate(),
                "latency_ms_avg": self._calculate_avg_latency(),
                "records_processed": self.totals["events"],
                # Step-2 admission metrics (for convenience include top-level keys)
                "http_admitted_total": self.http_admitted_total,
                "http_dropped_total": self.http_dropped_total.copy(),
                "udp_admitted_total": self.udp_admitted_total,
                "udp_dropped_total": self.udp_dropped_total.copy(),
                "queue_depth": 0,  # TODO: get from queue
                "records_queued": 0,  # TODO: get from queue
                "eps": eps_1m,
                
                "totals": {
                    "events": self.totals["events"],
                    "batches": self.totals["batches"],
                    "threat_matches": self.totals["threat_matches"],
                    "unique_sources": len(self.totals["unique_sources"]),
                    "risk_sum": self.totals["risk_sum"],
                    "risk_count": self.totals["risk_count"],
                    "blocked_sources": self.totals["blocked_sources"]
                },
                
                "blocked_sources": self.blocked_sources.copy(),
                
                "rates": {
                    "eps_1m": eps_1m,
                    "epm_1m": epm_1m,
                    "bpm_1m": bpm_1m
                },
                
                "queue": {
                    "lag_ms_p50": lag_p50,
                    "lag_ms_p95": lag_p95,
                    "lag_ms_p99": lag_p99
                },
                
                "timeseries": {
                    "last_5m": self.timeseries.copy()
                },
                "export": {
                    "sent_total": self.export_sent_total.copy(),
                    "failed_total": self.export_failed_total.copy(),
                    "test_total": self.export_test_total.copy()
                },
                "source_admitted_total": self.source_admitted_total.copy(),
                "source_dropped_total": self.source_dropped_total.copy(),
                "udp_head": self._get_udp_head_metrics(),
                # P1: Additional UDP head metrics
                "udp_head_packets_total": self._get_udp_head_metrics().get("packets_total", 0),
                "udp_head_bytes_total": self._get_udp_head_metrics().get("bytes_total", 0),
                "udp_head_last_packet_ts": self._get_udp_head_metrics().get("last_packet_ts", 0.0),
                # P1 T4: Output test metrics
                "outputs_test_success_total": self.outputs_test_success_total.copy(),
                "outputs_test_fail_total": self.outputs_test_fail_total.copy()
            }
            
    def record_event(self, risk_score: int, threat_matches: int):
        """Record a single event for window tracking and totals"""
        with self.lock:
            # Update totals
            self.totals["events"] += 1
            self.totals["threat_matches"] += threat_matches
            self.totals["risk_sum"] += risk_score
            self.totals["risk_count"] += 1
            
            # Add to sliding windows
            self.eps_window.append(1)  # 1 event this second
            if threat_matches > 0:
                self.threats_window.append(threat_matches)
            self.risk_window.append(risk_score)
    
    def _calculate_success_rate(self) -> float:
        """Calculate success rate for last 15 minutes"""
        if self.requests_total == 0:
            return 0.0
        return round((self.requests_success / self.requests_total) * 100, 2)
    
    def _calculate_avg_latency(self) -> float:
        """Calculate average latency from samples"""
        if not self.latency_samples:
            return 0.0
        return round(statistics.mean(self.latency_samples), 2)

# Global metrics instance
metrics = MetricsAggregator()

def get_metrics() -> Dict[str, Any]:
    """Get current metrics"""
    return metrics.get_metrics()

def increment_requests(failed: bool = False, latency_ms: float = None):
    """Increment request counters"""
    metrics.increment_requests(failed, latency_ms)

def record_batch(record_count: int, threat_matches: int, risk_scores: List[int], sources: List[str]):
    """Record a processed batch"""
    metrics.record_batch(record_count, threat_matches, risk_scores, sources)

def record_queue_lag(lag_ms: int):
    """Record queue lag measurement"""
    metrics.record_queue_lag(lag_ms)

def record_event(risk_score: int, threat_matches: int):
    """Record a single event for window tracking"""
    metrics.record_event(risk_score, threat_matches)

def record_blocked_source(source_id: str, reason: str):
    """Record a blocked source admission"""
    metrics.record_blocked_source(source_id, reason)

def record_fifo_dropped(count: int = 1):
    """Record FIFO dropped events"""
    prometheus_metrics.increment_fifo_dropped(count)

def record_udp_packets_received(count: int = 1):
    """Record UDP packets received"""
    prometheus_metrics.increment_udp_packets_received(count)

def record_records_parsed(count: int = 1):
    """Record successfully parsed records"""
    prometheus_metrics.increment_records_parsed(count)

def record_export_sent(dest: str, count: int = 1):
    """Record successfully exported events"""
    metrics.record_export_sent(dest, count)

def record_export_failed(dest: str, reason: str, count: int = 1):
    """Record failed export events"""
    metrics.record_export_failed(dest, reason, count)

def record_export_test(dest: str, count: int = 1):
    """Record export test attempts"""
    metrics.record_export_test(dest, count)

def record_outputs_test_success(target: str):
    """Record successful output test"""
    metrics.record_outputs_test_success(target)

def record_outputs_test_fail(target: str):
    """Record failed output test"""
    metrics.record_outputs_test_fail(target)

def record_source_admitted(source_id: str, count: int = 1):
    """Record admitted events for source"""
    metrics.record_source_admitted(source_id, count)

def record_source_dropped(source_id: str, reason: str, count: int = 1):
    """Record dropped events for source"""
    metrics.record_source_dropped(source_id, reason, count)

def update_source_eps(source_id: str, eps: float):
    """Update source EPS ring buffer"""
    metrics.update_source_eps(source_id, eps)

def update_source_error_pct(source_id: str, error_pct: float):
    """Update source error percentage ring buffer"""
    metrics.update_source_error_pct(source_id, error_pct)

def get_source_eps_1m(source_id: str) -> float:
    """Get 1-minute average EPS for source"""
    return metrics.get_source_eps_1m(source_id)

def get_source_error_pct_1m(source_id: str) -> float:
    """Get 1-minute average error percentage for source"""
    return metrics.get_source_error_pct_1m(source_id)

def tick():
    """Background tick to roll windows"""
    metrics.tick()
