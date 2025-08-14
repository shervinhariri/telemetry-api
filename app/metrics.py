import time
import threading
from collections import deque
from typing import Dict, Any, List, Optional
import statistics

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
            "risk_count": 0
        }
        
        # Request counters
        self.requests_total = 0
        self.requests_failed = 0
        
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
        
    def increment_requests(self, failed: bool = False):
        """Increment request counters"""
        with self.lock:
            self.requests_total += 1
            if failed:
                self.requests_failed += 1
                
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
            
    def record_queue_lag(self, lag_ms: int):
        """Record queue lag measurement"""
        with self.lock:
            self.lag_samples.append(lag_ms)
            
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
                "records_processed": self.totals["events"],
                "queue_depth": 0,  # TODO: get from queue
                "records_queued": 0,  # TODO: get from queue
                "eps": eps_1m,
                
                "totals": {
                    "events": self.totals["events"],
                    "batches": self.totals["batches"],
                    "threat_matches": self.totals["threat_matches"],
                    "unique_sources": len(self.totals["unique_sources"]),
                    "risk_sum": self.totals["risk_sum"],
                    "risk_count": self.totals["risk_count"]
                },
                
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
                }
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

# Global metrics instance
metrics = MetricsAggregator()

def get_metrics() -> Dict[str, Any]:
    """Get current metrics"""
    return metrics.get_metrics()

def increment_requests(failed: bool = False):
    """Increment request counters"""
    metrics.increment_requests(failed)

def record_batch(record_count: int, threat_matches: int, risk_scores: List[int], sources: List[str]):
    """Record a processed batch"""
    metrics.record_batch(record_count, threat_matches, risk_scores, sources)

def record_queue_lag(lag_ms: int):
    """Record queue lag measurement"""
    metrics.record_queue_lag(lag_ms)

def record_event(risk_score: int, threat_matches: int):
    """Record a single event for window tracking"""
    metrics.record_event(risk_score, threat_matches)

def tick():
    """Background tick to roll windows"""
    metrics.tick()
