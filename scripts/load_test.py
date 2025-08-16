#!/usr/bin/env python3
"""
Load test script for Telemetry API v0.7.8
Generates 1,000 requests over 2 minutes with mixed methods and payloads
"""

import requests
import json
import time
import random
import threading
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://localhost:8080"
API_KEY = "TEST_KEY"
TOTAL_REQUESTS = 1000
DURATION_SECONDS = 120  # 2 minutes

# Sample data for different request types
ZEEK_SAMPLES = [
    {
        "ts": 1642176000.0,
        "uid": "C1234567890abcdef",
        "id.orig_h": "192.168.1.100",
        "id.orig_p": 54321,
        "id.resp_h": "8.8.8.8",
        "id.resp_p": 53,
        "proto": "udp",
        "service": "dns",
        "duration": 0.123,
        "orig_bytes": 64,
        "resp_bytes": 128,
        "conn_state": "SF"
    },
    {
        "ts": 1642176005.0,
        "uid": "C1234567890abcdef1",
        "id.orig_h": "192.168.1.101",
        "id.orig_p": 12345,
        "id.resp_h": "1.1.1.1",
        "id.resp_p": 443,
        "proto": "tcp",
        "service": "ssl",
        "duration": 5.678,
        "orig_bytes": 1024,
        "resp_bytes": 2048,
        "conn_state": "SF"
    }
]

NETFLOW_SAMPLES = [
    {
        "timestamp": 1642176000,
        "src_ip": "192.168.1.100",
        "dst_ip": "8.8.8.8",
        "src_port": 54321,
        "dst_port": 53,
        "protocol": 17,
        "bytes": 192,
        "packets": 2,
        "device": "router-01",
        "exporter": "192.168.1.1"
    },
    {
        "timestamp": 1642176005,
        "src_ip": "192.168.1.101",
        "dst_ip": "1.1.1.1",
        "src_port": 12345,
        "dst_port": 443,
        "protocol": 6,
        "bytes": 3072,
        "packets": 18,
        "device": "router-01",
        "exporter": "192.168.1.1"
    }
]

INDICATOR_SAMPLES = [
    {"ip_or_cidr": "10.0.0.0/24", "category": "internal", "confidence": 90},
    {"ip_or_cidr": "172.16.0.0/16", "category": "dmz", "confidence": 80},
    {"ip_or_cidr": "192.168.0.0/16", "category": "private", "confidence": 70}
]

class LoadTestStats:
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.status_codes = {}
        self.latencies = []
        self.threat_matches = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
    
    def record_request(self, status_code: int, latency: float, threat_matches: int = 0):
        with self.lock:
            self.total_requests += 1
            if 200 <= status_code < 300:
                self.successful_requests += 1
            else:
                self.failed_requests += 1
            
            self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
            self.latencies.append(latency)
            self.threat_matches += threat_matches
    
    def get_summary(self) -> Dict[str, Any]:
        with self.lock:
            duration = time.time() - self.start_time
            eps = self.total_requests / duration if duration > 0 else 0
            
            # Calculate percentiles
            sorted_latencies = sorted(self.latencies)
            p50 = sorted_latencies[len(sorted_latencies) // 2] if sorted_latencies else 0
            p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)] if sorted_latencies else 0
            
            error_rate = (self.failed_requests / self.total_requests * 100) if self.total_requests > 0 else 0
            
            return {
                "total_requests": self.total_requests,
                "successful": self.successful_requests,
                "failed": self.failed_requests,
                "status_codes": dict(self.status_codes),
                "eps": round(eps, 2),
                "p50_latency_ms": round(p50 * 1000, 2),
                "p95_latency_ms": round(p95 * 1000, 2),
                "error_rate_pct": round(error_rate, 2),
                "threat_matches": self.threat_matches,
                "duration_seconds": round(duration, 2)
            }

def make_request(method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make a request to the API"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    start_time = time.time()
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        latency = time.time() - start_time
        
        # Extract threat matches from response if available
        threat_matches = 0
        if response.status_code == 200:
            try:
                result = response.json()
                if isinstance(result, dict):
                    # Look for threat matches in various response formats
                    if "ti" in result and "matches" in result["ti"]:
                        threat_matches = len(result["ti"]["matches"])
                    elif "threat_matches" in result:
                        threat_matches = result["threat_matches"]
            except:
                pass
        
        return {
            "status_code": response.status_code,
            "latency": latency,
            "threat_matches": threat_matches,
            "success": 200 <= response.status_code < 300
        }
        
    except Exception as e:
        latency = time.time() - start_time
        return {
            "status_code": 0,
            "latency": latency,
            "threat_matches": 0,
            "success": False,
            "error": str(e)
        }

def generate_zeek_payload() -> List[Dict[str, Any]]:
    """Generate a random Zeek payload"""
    count = random.randint(1, 200)
    records = []
    
    for i in range(count):
        base_record = random.choice(ZEEK_SAMPLES).copy()
        base_record["ts"] = time.time() + random.uniform(-3600, 0)  # Random time in last hour
        base_record["uid"] = f"C{random.randint(1000000000, 9999999999)}"
        base_record["id.orig_h"] = f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"
        base_record["id.resp_h"] = f"{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
        records.append(base_record)
    
    return records

def generate_netflow_payload() -> List[Dict[str, Any]]:
    """Generate a random NetFlow payload"""
    count = random.randint(1, 200)
    records = []
    
    for i in range(count):
        base_record = random.choice(NETFLOW_SAMPLES).copy()
        base_record["timestamp"] = int(time.time()) + random.randint(-3600, 0)
        base_record["src_ip"] = f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"
        base_record["dst_ip"] = f"{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
        records.append(base_record)
    
    return records

def generate_malformed_payload() -> List[Dict[str, Any]]:
    """Generate a malformed payload (10% of requests)"""
    return [{"invalid": "data", "missing_required_fields": True}]

def make_zeek_request(stats: LoadTestStats):
    """Make a Zeek ingest request"""
    if random.random() < 0.1:  # 10% malformed
        payload = generate_malformed_payload()
    else:
        payload = generate_zeek_payload()
    
    result = make_request("POST", "/v1/ingest/zeek", payload)
    stats.record_request(result["status_code"], result["latency"], result["threat_matches"])

def make_netflow_request(stats: LoadTestStats):
    """Make a NetFlow ingest request"""
    if random.random() < 0.1:  # 10% malformed
        payload = generate_malformed_payload()
    else:
        payload = generate_netflow_payload()
    
    result = make_request("POST", "/v1/ingest/netflow", payload)
    stats.record_request(result["status_code"], result["latency"], result["threat_matches"])

def make_indicator_request(stats: LoadTestStats):
    """Make a threat indicator request"""
    payload = random.choice(INDICATOR_SAMPLES).copy()
    payload["ip_or_cidr"] = f"{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}.0/24"
    
    result = make_request("PUT", "/v1/indicators", payload)
    stats.record_request(result["status_code"], result["latency"], result["threat_matches"])

def make_delete_request(stats: LoadTestStats):
    """Make a delete indicator request (some will be 404s)"""
    indicator_id = f"{random.randint(10000000, 99999999)}"
    result = make_request("DELETE", f"/v1/indicators/{indicator_id}")
    stats.record_request(result["status_code"], result["latency"], result["threat_matches"])

def worker(stats: LoadTestStats):
    """Worker function for load testing"""
    while stats.total_requests < TOTAL_REQUESTS:
        # Randomly choose request type based on distribution
        rand = random.random()
        
        if rand < 0.6:  # 60% Zeek
            make_zeek_request(stats)
        elif rand < 0.9:  # 30% NetFlow
            make_netflow_request(stats)
        elif rand < 0.95:  # 5% PUT indicators
            make_indicator_request(stats)
        else:  # 5% DELETE indicators
            make_delete_request(stats)
        
        # Small delay to spread requests over time
        time.sleep(DURATION_SECONDS / TOTAL_REQUESTS)

def main():
    """Main load test function"""
    print("🚀 Starting Telemetry API v0.7.8 Load Test")
    print(f"Target: {TOTAL_REQUESTS} requests over {DURATION_SECONDS} seconds")
    print(f"Distribution: 60% Zeek, 30% NetFlow, 5% PUT indicators, 5% DELETE indicators")
    print(f"Base URL: {BASE_URL}")
    print()
    
    # Check if API is available
    try:
        response = requests.get(f"{BASE_URL}/v1/health", timeout=5)
        if response.status_code != 200:
            print("❌ API not available")
            return 1
    except:
        print("❌ Cannot connect to API")
        return 1
    
    print("✅ API is available, starting load test...")
    print()
    
    stats = LoadTestStats()
    
    # Start workers
    num_workers = min(10, TOTAL_REQUESTS // 100)  # Scale workers based on request count
    print(f"Starting {num_workers} workers...")
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(worker, stats) for _ in range(num_workers)]
        
        # Monitor progress
        start_time = time.time()
        while stats.total_requests < TOTAL_REQUESTS:
            time.sleep(5)
            elapsed = time.time() - start_time
            progress = (stats.total_requests / TOTAL_REQUESTS) * 100
            eps = stats.total_requests / elapsed if elapsed > 0 else 0
            print(f"Progress: {stats.total_requests}/{TOTAL_REQUESTS} ({progress:.1f}%) - {eps:.1f} req/s")
        
        # Wait for completion
        for future in futures:
            future.cancel()
    
    # Print final results
    print()
    print("📊 Load Test Complete!")
    print("=" * 50)
    
    summary = stats.get_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    print()
    print("Status Code Breakdown:")
    for code, count in summary["status_codes"].items():
        print(f"  {code}: {count}")
    
    print()
    if summary["error_rate_pct"] < 5:
        print("🎉 Load test passed! Error rate < 5%")
        return 0
    else:
        print("⚠️  Load test completed with high error rate")
        return 1

if __name__ == "__main__":
    exit(main())
