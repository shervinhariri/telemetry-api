#!/usr/bin/env python3
"""
Test script for Telemetry API v0.7.8 endpoints
"""

import requests
import json
import time
import random
from typing import Dict, Any

BASE_URL = "http://localhost:8080"
API_KEY = "TEST_KEY"

def make_request(method: str, endpoint: str, data: Dict[str, Any] = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
    """Make a request to the API"""
    url = f"{BASE_URL}{endpoint}"
    auth_headers = {"Authorization": f"Bearer {API_KEY}"}
    
    if headers:
        auth_headers.update(headers)
    
    try:
        if method == "GET":
            response = requests.get(url, headers=auth_headers)
        elif method == "POST":
            response = requests.post(url, json=data, headers=auth_headers)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=auth_headers)
        elif method == "DELETE":
            response = requests.delete(url, headers=auth_headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ {method} {endpoint} failed: {e}")
        return None

def test_health():
    """Test health endpoint"""
    print("🔍 Testing /v1/health...")
    response = requests.get(f"{BASE_URL}/v1/health")
    if response.status_code == 200:
        print("✅ Health check passed")
        return True
    else:
        print(f"❌ Health check failed: {response.status_code}")
        return False

def test_version():
    """Test version endpoint"""
    print("🔍 Testing /v1/version...")
    result = make_request("GET", "/v1/version")
    if result and result.get("version"):
        print(f"✅ Version check passed: {result.get('version')}")
        return True
    else:
        print(f"❌ Version check failed: {result}")
        return False

def test_ingest_zeek():
    """Test Zeek ingest endpoint"""
    print("🔍 Testing /v1/ingest/zeek...")
    
    # Load sample data
    with open("samples/zeek_conn_small.json", "r") as f:
        zeek_data = json.load(f)
    
    result = make_request("POST", "/v1/ingest/zeek", zeek_data)
    if result and result.get("accepted", 0) > 0:
        print(f"✅ Zeek ingest passed: {result.get('accepted')} records accepted")
        return True
    else:
        print(f"❌ Zeek ingest failed: {result}")
        return False

def test_ingest_netflow():
    """Test NetFlow ingest endpoint"""
    print("🔍 Testing /v1/ingest/netflow...")
    
    # Load sample data
    with open("samples/netflow_small.json", "r") as f:
        netflow_data = json.load(f)
    
    result = make_request("POST", "/v1/ingest/netflow", netflow_data)
    if result and result.get("accepted", 0) > 0:
        print(f"✅ NetFlow ingest passed: {result.get('accepted')} records accepted")
        return True
    else:
        print(f"❌ NetFlow ingest failed: {result}")
        return False

def test_ingest_bulk():
    """Test bulk ingest endpoint"""
    print("🔍 Testing /v1/ingest/bulk...")
    
    # Load sample data
    with open("samples/zeek_conn_small.json", "r") as f:
        zeek_data = json.load(f)
    
    bulk_data = {
        "type": "zeek",
        "records": zeek_data
    }
    
    result = make_request("POST", "/v1/ingest/bulk", bulk_data)
    if result and result.get("accepted", 0) > 0:
        print(f"✅ Bulk ingest passed: {result.get('accepted')} records accepted")
        return True
    else:
        print(f"❌ Bulk ingest failed: {result}")
        return False

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
    if result and result.get("status") == "added":
        indicator_id = result.get("id")
        print(f"✅ Add indicator passed: {indicator_id}")
        
        # Test deleting indicator
        delete_result = make_request("DELETE", f"/v1/indicators/{indicator_id}")
        if delete_result and delete_result.get("status") == "deleted":
            print(f"✅ Delete indicator passed: {indicator_id}")
            return True
        else:
            print(f"❌ Delete indicator failed: {delete_result}")
            return False
    else:
        print(f"❌ Add indicator failed: {result}")
        return False

def test_download():
    """Test download endpoint"""
    print("🔍 Testing /v1/download/json...")
    
    # For streaming endpoints, we need to handle the response differently
    try:
        response = requests.get(
            "http://localhost:8080/v1/download/json?limit=10",
            headers={"Authorization": "Bearer TEST_KEY"},
            stream=True
        )
        if response.status_code == 200:
            print("✅ Download endpoint accessible")
            return True
        else:
            print(f"❌ Download endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Download endpoint failed: {e}")
        return False

def test_requests_api():
    """Test requests API endpoint"""
    print("🔍 Testing /v1/api/requests...")
    
    result = make_request("GET", "/v1/api/requests?limit=10&window=15m")
    if result and "items" in result:
        print(f"✅ Requests API passed: {len(result.get('items', []))} requests")
        return True
    else:
        print(f"❌ Requests API failed: {result}")
        return False

def test_metrics():
    """Test metrics endpoint"""
    print("🔍 Testing /v1/metrics...")
    
    result = make_request("GET", "/v1/metrics")
    if result and isinstance(result, dict):
        print("✅ Metrics endpoint passed")
        return True
    else:
        print(f"❌ Metrics endpoint failed: {result}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Telemetry API v0.7.8 endpoint tests...")
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
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
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
