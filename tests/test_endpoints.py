#!/usr/bin/env python3
"""
Test script for Telemetry API v0.8.1 endpoints
"""

import requests
import json
import time
import random
import os
from typing import Dict, Any

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:80")
API_KEY = os.getenv("API_KEY", "TEST_ADMIN_KEY")
AUTH     = f"Bearer {API_KEY}"

def make_request(method: str, path: str, payload=None):
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": AUTH, "Content-Type": "application/json"}
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers)
        elif method == "POST":
            resp = requests.post(url, json=payload, headers=headers)
        elif method == "PUT":
            resp = requests.put(url, json=payload, headers=headers)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method {method}")
        resp.raise_for_status()
        return resp.json() if resp.content else {}
    except requests.exceptions.RequestException as e:
        print(f"❌ {method} {path} failed: {e}")
        return None

def test_health():
    """Test health endpoint"""
    print("🔍 Testing /v1/health...")
    response = requests.get(f"{BASE_URL}/v1/health")
    assert response.status_code == 200, f"Health check failed: {response.status_code}"
    print("✅ Health check passed")

def test_version():
    """Test version endpoint"""
    print("🔍 Testing /v1/version...")
    result = make_request("GET", "/v1/version")
    assert result is not None, "Version request failed"
    assert result.get("version"), f"Version check failed: {result}"
    print(f"✅ Version check passed: {result.get('version')}")

def test_ingest_zeek():
    """Test Zeek ingest endpoint"""
    print("🔍 Testing /v1/ingest/zeek...")
    
    # Use canonical JSON array format for /v1/ingest
    zeek_data = [
        {
            "ts": 1723351200.456,
            "uid": "C1234567890abcdef",
            "id.orig_h": "10.1.2.3",
            "id.orig_p": 55342,
            "id.resp_h": "8.8.8.8",
            "id.resp_p": 53,
            "proto": "udp",
            "service": "dns",
            "duration": 0.025,
            "orig_bytes": 78,
            "resp_bytes": 256
        }
    ]
    
    result = make_request("POST", "/v1/ingest", zeek_data)
    assert result is not None, "Zeek ingest request failed"
    assert result.get("status") == "accepted", f"Zeek ingest failed: {result}"
    print(f"✅ Zeek ingest passed: {result.get('records_processed')} records processed")

def test_ingest_netflow():
    """Test NetFlow ingest endpoint"""
    print("🔍 Testing /v1/ingest/netflow...")
    
    # Use canonical JSON array format for /v1/ingest
    netflow_data = [
        {
            "ts": 1723351200.456,
            "src_ip": "192.168.1.100",
            "dst_ip": "1.1.1.1",
            "src_port": 12345,
            "dst_port": 80,
            "proto": "tcp",
            "bytes": 1024,
            "packets": 10
        }
    ]
    
    result = make_request("POST", "/v1/ingest", netflow_data)
    assert result is not None, "NetFlow ingest request failed"
    assert result.get("status") == "accepted", f"NetFlow ingest failed: {result}"
    print(f"✅ NetFlow ingest passed: {result.get('records_processed')} records processed")

def test_ingest_bulk():
    """Test bulk ingest endpoint"""
    print("🔍 Testing /v1/ingest/bulk...")
    
    # Create sample data instead of loading from file
    zeek_data = [
        {
            "ts": 1723351200.456,
            "uid": "C1234567890",
            "id.orig_h": "10.1.2.3",
            "id.orig_p": 55342,
            "id.resp_h": "8.8.8.8",
            "id.resp_p": 53,
            "proto": "udp",
            "service": "dns",
            "duration": 0.025,
            "orig_bytes": 78,
            "resp_bytes": 256
        }
    ]
    
    bulk_data = {
        "collector_id": "test-collector",
        "format": "zeek",
        "records": zeek_data
    }
    
    # Debug: print the payload being sent
    print(f"📤 Sending payload: {json.dumps(bulk_data, indent=2)}")
    
    # Make request with better error handling
    url = f"{BASE_URL}/v1/ingest/bulk"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=bulk_data, headers=headers)
        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response headers: {dict(response.headers)}")
        print(f"📥 Response body: {response.text}")
        
        response.raise_for_status()
        result = response.json()
        assert result.get("status") == "accepted", f"Bulk ingest failed: {result}"
        print(f"✅ Bulk ingest passed: {result.get('records_processed')} records processed")
    except requests.exceptions.RequestException as e:
        print(f"❌ Bulk ingest failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"❌ Response status: {e.response.status_code}")
            print(f"❌ Response body: {e.response.text}")
        assert False, f"Bulk ingest request failed: {e}"

def test_indicators():
    """Test threat intelligence endpoints"""
    print("🔍 Testing /v1/indicators...")
    
    # Test adding indicator
    indicator_data = {
        "ip_or_cidr": "192.168.1.0/24",
        "category": "test",
        "confidence": 90
    }
    
    result = make_request("PUT", "/v1/indicators", indicator_data)
    assert result is not None, "Add indicator request failed"
    assert result.get("status") == "added", f"Add indicator failed: {result}"
    indicator_id = result.get("id")
    print(f"✅ Add indicator passed: {indicator_id}")
    
    # Test deleting indicator
    delete_result = make_request("DELETE", f"/v1/indicators/{indicator_id}")
    assert delete_result is not None, "Delete indicator request failed"
    assert delete_result.get("status") == "deleted", f"Delete indicator failed: {delete_result}"
    print(f"✅ Delete indicator passed: {indicator_id}")

def test_download():
    """Test download endpoint"""
    print("🔍 Testing /v1/download/json...")
    
    # For streaming endpoints, we need to handle the response differently
    try:
        response = requests.get(
            f"{BASE_URL}/v1/download/json?limit=10",
            headers={"Authorization": f"Bearer {API_KEY}"},
            stream=True
        )
        assert response.status_code == 200, f"Download endpoint failed: {response.status_code}"
        print("✅ Download endpoint accessible")
    except Exception as e:
        assert False, f"Download endpoint failed: {e}"

def test_requests_api():
    """Test requests API endpoint"""
    print("🔍 Testing /v1/api/requests...")
    
    result = make_request("GET", "/v1/api/requests?limit=10&window=15m")
    assert result is not None, "Requests API request failed"
    assert "items" in result, f"Requests API failed: {result}"
    print(f"✅ Requests API passed: {len(result.get('items', []))} requests")

def test_metrics():
    """Test metrics endpoint"""
    print("🔍 Testing /v1/metrics...")
    
    result = make_request("GET", "/v1/metrics")
    assert result is not None, "Metrics request failed"
    assert isinstance(result, dict), f"Metrics endpoint failed: {result}"
    print("✅ Metrics endpoint passed")

def main():
    """Run all tests"""
    print("🚀 Starting Telemetry API v0.8.1 endpoint tests...")
    print(f"Base URL: {BASE_URL}")
    print(f"API Key: {API_KEY}")
    print()
    
    tests = [
        test_health,
        test_version,
        test_ingest_zeek,
        test_ingest_netflow,
        test_ingest_bulk,
        test_indicators,
        test_download,
        test_requests_api,
        test_metrics
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
        print()
    
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    exit(main())
