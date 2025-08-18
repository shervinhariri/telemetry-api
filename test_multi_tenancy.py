#!/usr/bin/env python3
"""
Test script for multi-tenancy functionality
"""
import requests
import json

BASE_URL = "http://localhost:8000"
ADMIN_KEY = "DEV_ADMIN_KEY_f0caf48c57"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/v1/health", headers={"Authorization": f"Bearer {ADMIN_KEY}"})
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_tenant_override():
    """Test tenant override functionality"""
    print("\nTesting tenant override...")
    response = requests.get(
        f"{BASE_URL}/v1/health", 
        headers={
            "Authorization": f"Bearer {ADMIN_KEY}",
            "X-Tenant-ID": "default"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_ingest():
    """Test ingest endpoint"""
    print("\nTesting ingest endpoint...")
    data = {
        "records": [
            {
                "ts": "2023-01-01T00:00:00Z",
                "src_ip": "192.168.1.1",
                "dst_ip": "8.8.8.8"
            }
        ]
    }
    response = requests.post(
        f"{BASE_URL}/v1/ingest",
        headers={
            "Authorization": f"Bearer {ADMIN_KEY}",
            "Content-Type": "application/json"
        },
        json=data
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    else:
        print(f"Error: {response.text}")
    return response.status_code == 200

def test_metrics():
    """Test metrics endpoint"""
    print("\nTesting metrics endpoint...")
    response = requests.get(f"{BASE_URL}/v1/metrics", headers={"Authorization": f"Bearer {ADMIN_KEY}"})
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    else:
        print(f"Error: {response.text}")
    return response.status_code == 200

def main():
    print("Testing Multi-Tenancy Implementation")
    print("=" * 40)
    
    tests = [
        ("Health Endpoint", test_health),
        ("Tenant Override", test_tenant_override),
        ("Ingest Endpoint", test_ingest),
        ("Metrics Endpoint", test_metrics),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"Error in {test_name}: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 40)
    print("Test Results:")
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")

if __name__ == "__main__":
    main()
