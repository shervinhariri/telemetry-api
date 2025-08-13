#!/usr/bin/env python3
"""
Test script for Fix Pack v0.3 - Enrichment and Live Metrics
"""

import json
import time
import random
import requests
import ipaddress
from typing import Dict, Any

def rand_ip() -> str:
    """Generate random IP with some hits in threat ranges"""
    if random.random() < 0.1:
        return f"45.149.3.{random.randint(1, 254)}"
    return str(ipaddress.IPv4Address(random.randint(0, 2**32-1)))

def create_event() -> Dict[str, Any]:
    """Create a sample event"""
    return {
        "src_ip": rand_ip(),
        "dst_ip": "8.8.8.8",
        "src_port": random.randint(1024, 65535),
        "dst_port": random.choice([53, 80, 443, 445, 3389, 1433, 22, 23]),
        "bytes": random.randint(200, 5_000_000),
        "proto": random.choice(["tcp", "udp"]),
        "ts": int(time.time() * 1000)
    }

def test_ingest():
    """Test the ingest endpoint"""
    print("🧪 Testing /v1/ingest...")
    
    # Create batch of events
    events = [create_event() for _ in range(100)]
    
    response = requests.post(
        "http://localhost:8080/v1/ingest",
        headers={"Authorization": "Bearer TEST_KEY"},
        json={"records": events}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Ingest successful: {result}")
        return True
    else:
        print(f"❌ Ingest failed: {response.status_code} - {response.text}")
        return False

def test_metrics():
    """Test the metrics endpoint"""
    print("\n📊 Testing /v1/metrics...")
    
    response = requests.get("http://localhost:8080/v1/metrics")
    
    if response.status_code == 200:
        metrics = response.json()
        print("✅ Metrics response structure:")
        print(f"  - requests_total: {metrics.get('requests_total', 0)}")
        print(f"  - records_processed: {metrics.get('records_processed', 0)}")
        print(f"  - rates.epm_1m: {metrics.get('rates', {}).get('epm_1m', 0)}")
        print(f"  - rates.bpm_1m: {metrics.get('rates', {}).get('bpm_1m', 0)}")
        print(f"  - queue.lag_ms_p95: {metrics.get('queue', {}).get('lag_ms_p95', 0)}")
        
        # Check for timeseries data
        timeseries = metrics.get('timeseries', {}).get('last_5m', {})
        if timeseries:
            print(f"  - timeseries.eps points: {len(timeseries.get('eps', []))}")
            print(f"  - timeseries.threats points: {len(timeseries.get('threats', []))}")
        
        return True
    else:
        print(f"❌ Metrics failed: {response.status_code} - {response.text}")
        return False

def test_lookup():
    """Test the lookup endpoint"""
    print("\n🔍 Testing /v1/lookup...")
    
    response = requests.post(
        "http://localhost:8080/v1/lookup",
        headers={"Authorization": "Bearer TEST_KEY", "Content-Type": "application/json"},
        json={"ip": "8.8.8.8"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Lookup response:")
        print(f"  - geo: {result.get('geo')}")
        print(f"  - asn: {result.get('asn')}")
        print(f"  - ti.matches: {result.get('ti', {}).get('matches', [])}")
        print(f"  - risk_score: {result.get('risk_score', 0)}")
        return True
    else:
        print(f"❌ Lookup failed: {response.status_code} - {response.text}")
        return False

def test_threat_matching():
    """Test threat matching with known bad IPs"""
    print("\n⚠️ Testing threat matching...")
    
    # Test with IP in our threat list
    response = requests.post(
        "http://localhost:8080/v1/lookup",
        headers={"Authorization": "Bearer TEST_KEY", "Content-Type": "application/json"},
        json={"ip": "45.149.3.100"}
    )
    
    if response.status_code == 200:
        result = response.json()
        matches = result.get('ti', {}).get('matches', [])
        risk_score = result.get('risk_score', 0)
        
        print(f"✅ Threat IP lookup:")
        print(f"  - matches: {matches}")
        print(f"  - risk_score: {risk_score}")
        
        if matches:
            print("✅ Threat matching working!")
        else:
            print("⚠️ No threat matches found (check indicators.txt)")
        
        return True
    else:
        print(f"❌ Threat lookup failed: {response.status_code}")
        return False

def main():
    """Run all tests"""
    print("🚀 Fix Pack v0.3 Test Suite")
    print("=" * 40)
    
    # Wait for service to be ready
    print("⏳ Waiting for service to be ready...")
    time.sleep(5)
    
    tests = [
        test_ingest,
        test_metrics,
        test_lookup,
        test_threat_matching
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print(f"\n📈 Test Results: {passed}/{len(tests)} passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! Fix Pack v0.3 is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the implementation.")

if __name__ == "__main__":
    main()
