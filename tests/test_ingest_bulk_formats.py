#!/usr/bin/env python3
"""
Unit tests for bulk ingest endpoint formats
"""

import pytest
import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost"
API_KEY = "DEV_ADMIN_KEY_5a8f9ffdc3"

def get_metrics_before():
    """Get metrics before test"""
    try:
        response = requests.get(f"{BASE_URL}/v1/metrics", headers={"Authorization": f"Bearer {API_KEY}"})
        if response.status_code == 200:
            return response.text
    except:
        pass
    return ""

def get_metrics_after():
    """Get metrics after test"""
    try:
        response = requests.get(f"{BASE_URL}/v1/metrics", headers={"Authorization": f"Bearer {API_KEY}"})
        if response.status_code == 200:
            return response.text
    except:
        pass
    return ""

def test_bulk_array_accepts():
    """Test /v1/ingest/bulk with array format returns 2xx and increments metrics"""
    print("🔍 Testing /v1/ingest/bulk with array format...")
    
    # Get metrics before
    metrics_before = get_metrics_before()
    
    # Array format (canonical)
    array_data = [
        {"src_ip": "1.1.1.1", "dst_ip": "8.8.8.8", "bytes": 1234}
    ]
    
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    try:
        response = requests.post(f"{BASE_URL}/v1/ingest/bulk", json=array_data, headers=headers)
        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response body: {response.text}")
        
        # Assert 2xx response
        assert response.status_code in [200, 202], f"Expected 2xx, got {response.status_code}"
        
        result = response.json()
        assert result.get("status") == "accepted", f"Bulk array failed: {result}"
        assert result.get("records_processed") == 1, f"Expected 1 record processed, got {result.get('records_processed')}"
        
        print(f"✅ Bulk array passed: {result.get('records_processed')} records processed")
        
        # Check metrics moved
        metrics_after = get_metrics_after()
        if metrics_before and metrics_after:
            # Simple check that metrics changed
            assert metrics_before != metrics_after, "Metrics should have changed"
            print("✅ Metrics observed")
        
        return True
    except Exception as e:
        print(f"❌ Bulk array failed: {e}")
        return False

def test_bulk_object_records_accepts():
    """Test /v1/ingest/bulk with object.records format returns 2xx"""
    print("🔍 Testing /v1/ingest/bulk with object.records format...")
    
    # Get metrics before
    metrics_before = get_metrics_before()
    
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
        
        # Assert 2xx response
        assert response.status_code in [200, 202], f"Expected 2xx, got {response.status_code}"
        
        result = response.json()
        assert result.get("status") == "accepted", f"Bulk object failed: {result}"
        assert result.get("records_processed") == 1, f"Expected 1 record processed, got {result.get('records_processed')}"
        
        print(f"✅ Bulk object passed: {result.get('records_processed')} records processed")
        
        # Check metrics moved
        metrics_after = get_metrics_after()
        if metrics_before and metrics_after:
            # Simple check that metrics changed
            assert metrics_before != metrics_after, "Metrics should have changed"
            print("✅ Metrics observed")
        
        return True
    except Exception as e:
        print(f"❌ Bulk object failed: {e}")
        return False

def test_bulk_invalid_shape_rejected():
    """Test /v1/ingest/bulk with invalid shape returns 422"""
    print("🔍 Testing /v1/ingest/bulk with invalid shape...")
    
    # Invalid shape (not array or object with records)
    invalid_data = "not json"
    
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    try:
        response = requests.post(f"{BASE_URL}/v1/ingest/bulk", data=invalid_data, headers=headers)
        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response body: {response.text}")
        
        # Should return 422 for invalid shape
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        
        result = response.json()
        assert result.get("error") == "bad_batch_shape", f"Expected bad_batch_shape error, got {result}"
        
        print("✅ Invalid shape correctly rejected")
        return True
    except Exception as e:
        print(f"❌ Invalid shape test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Running bulk format unit tests...")
    print(f"Base URL: {BASE_URL}")
    print(f"API Key: {API_KEY}")
    print()
    
    success = True
    success &= test_bulk_array_accepts()
    success &= test_bulk_object_records_accepts()
    success &= test_bulk_invalid_shape_rejected()
    
    if success:
        print("\n🎉 All bulk format unit tests passed!")
    else:
        print("\n❌ Some bulk format unit tests failed!")
        exit(1)
