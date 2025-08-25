#!/usr/bin/env python3
"""
Quick test for bulk endpoint formats
"""

import requests
import json

BASE_URL = "http://localhost"
API_KEY = "DEV_ADMIN_KEY_5a8f9ffdc3"

def test_bulk_array():
    """Test bulk endpoint with array format"""
    print("🔍 Testing /v1/ingest/bulk with array format...")
    
    # Array format (canonical)
    array_data = [
        {"src_ip": "1.1.1.1", "dst_ip": "8.8.8.8", "bytes": 1234}
    ]
    
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    try:
        response = requests.post(f"{BASE_URL}/v1/ingest/bulk", json=array_data, headers=headers)
        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response body: {response.text}")
        
        response.raise_for_status()
        result = response.json()
        assert result.get("status") == "accepted", f"Bulk array failed: {result}"
        print(f"✅ Bulk array passed: {result.get('records_processed')} records processed")
        return True
    except Exception as e:
        print(f"❌ Bulk array failed: {e}")
        return False

def test_bulk_object():
    """Test bulk endpoint with object format"""
    print("🔍 Testing /v1/ingest/bulk with object format...")
    
    # Object format (compatibility)
    object_data = {
        "collector_id": "test-collector",
        "format": "zeek",
        "records": [
            {"src_ip": "1.1.1.1", "dst_ip": "8.8.8.8", "bytes": 1234}
        ]
    }
    
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    try:
        response = requests.post(f"{BASE_URL}/v1/ingest/bulk", json=object_data, headers=headers)
        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response body: {response.text}")
        
        response.raise_for_status()
        result = response.json()
        assert result.get("status") == "accepted", f"Bulk object failed: {result}"
        print(f"✅ Bulk object passed: {result.get('records_processed')} records processed")
        return True
    except Exception as e:
        print(f"❌ Bulk object failed: {e}")
        return False

def main():
    print("🚀 Testing bulk endpoint formats...")
    print(f"Base URL: {BASE_URL}")
    print(f"API Key: {API_KEY}")
    print()
    
    success = True
    success &= test_bulk_array()
    success &= test_bulk_object()
    
    if success:
        print("\n🎉 All bulk format tests passed!")
    else:
        print("\n❌ Some bulk format tests failed!")
        exit(1)

if __name__ == "__main__":
    main()
