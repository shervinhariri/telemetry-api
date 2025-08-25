#!/usr/bin/env python3
"""
Test script for Ingest Limits feature implementation
Verifies all requirements from Step 2 execution plan
"""

import os
import json
import gzip
import time
import requests
import subprocess
import tempfile

# Test configuration
BASE_URL = "http://localhost"
API_KEY = "seed-7db78993"  # Use a seeded key from the logs

def test_size_limit_gzip():
    """Test 1: Oversize gz (6 MB) → expect 413"""
    print("=== Test 1: Size limit with gzip ===")
    
    # Create oversize gzipped data
    records = [{"id": i, "src_ip": f"1.1.1.{i%200}", "dst_ip": f"8.8.8.{i%200}"} for i in range(120000)]
    data = json.dumps(records).encode()
    gz_data = gzip.compress(data)
    
    print(f"Created gzipped data: {len(gz_data)} bytes")
    
    # Send request
    headers = {
        'Content-Type': 'application/json',
        'Content-Encoding': 'gzip',
        'Authorization': f'Bearer {API_KEY}'
    }
    
    response = requests.post(f"{BASE_URL}/v1/ingest", data=gz_data, headers=headers)
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    
    # Verify response
    assert response.status_code == 413, f"Expected 413, got {response.status_code}"
    
    try:
        error_data = response.json()
        assert error_data["error"] == "batch_too_large"
        assert error_data["limit_bytes"] == 5242880
        assert error_data["content_encoding"] == "gzip"
        print("✅ Size limit test passed")
    except Exception as e:
        print(f"❌ Size limit test failed: {e}")
        return False
    
    return True

def test_record_count_limit():
    """Test 2: 10001 records → expect 422"""
    print("\n=== Test 2: Record count limit ===")
    
    # Create 10001 records
    records = [{"id": i, "src_ip": f"1.1.1.{i%200}", "dst_ip": f"8.8.8.{i%200}"} for i in range(10001)]
    payload = {
        "collector_id": "test_collector",
        "format": "flows.v1",
        "records": records
    }
    
    data = json.dumps(payload).encode()
    print(f"Created payload with {len(records)} records: {len(data)} bytes")
    
    # Send request
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'
    }
    
    response = requests.post(f"{BASE_URL}/v1/ingest", data=data, headers=headers)
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    
    # Verify response
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    
    try:
        error_data = response.json()
        assert error_data["error"] == "too_many_records"
        assert error_data["limit"] == 10000
        assert error_data["observed"] == 10001
        print("✅ Record count limit test passed")
    except Exception as e:
        print(f"❌ Record count limit test failed: {e}")
        return False
    
    return True

def test_batch_shape_invalid():
    """Test 3: Invalid batch shape → expect 422"""
    print("\n=== Test 3: Invalid batch shape ===")
    
    # Create invalid shape (not JSON array or JSONL)
    invalid_data = '{"id":1}{"id":2}'.encode()
    print(f"Created invalid shape data: {len(invalid_data)} bytes")
    
    # Send request
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'
    }
    
    response = requests.post(f"{BASE_URL}/v1/ingest", data=invalid_data, headers=headers)
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    
    # Verify response
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    
    try:
        error_data = response.json()
        assert error_data["error"] == "bad_batch_shape"
        assert "expected JSON array or JSONL" in error_data["hint"]
        print("✅ Batch shape test passed")
    except Exception as e:
        print(f"❌ Batch shape test failed: {e}")
        return False
    
    return True

def test_valid_batch():
    """Test 4: Valid batch → expect 2xx"""
    print("\n=== Test 4: Valid batch ===")
    
    # Create valid batch with 250 records
    records = [{"id": i, "src_ip": f"1.1.1.{i%200}", "dst_ip": f"8.8.8.{i%200}"} for i in range(250)]
    payload = {
        "collector_id": "test_collector",
        "format": "flows.v1",
        "records": records
    }
    
    data = json.dumps(payload).encode()
    print(f"Created valid payload with {len(records)} records: {len(data)} bytes")
    
    # Send request
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'
    }
    
    response = requests.post(f"{BASE_URL}/v1/ingest", data=data, headers=headers)
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    
    # Verify response
    assert 200 <= response.status_code < 300, f"Expected 2xx, got {response.status_code}"
    
    try:
        success_data = response.json()
        assert success_data["status"] == "accepted"
        assert success_data["records_processed"] == 250
        print("✅ Valid batch test passed")
    except Exception as e:
        print(f"❌ Valid batch test failed: {e}")
        return False
    
    return True

def test_metrics():
    """Test 5: Check metrics are updated"""
    print("\n=== Test 5: Metrics verification ===")
    
    # Get metrics
    response = requests.get(f"{BASE_URL}/v1/metrics/prometheus")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    metrics_text = response.text
    
    # Check for ingest metrics
    metrics_to_check = [
        "telemetry_ingest_batches_total",
        "telemetry_ingest_reject_total",
        "telemetry_ingest_batch_bytes",
        "telemetry_ingest_records_per_batch"
    ]
    
    for metric in metrics_to_check:
        if metric in metrics_text:
            print(f"✅ Found metric: {metric}")
        else:
            print(f"❌ Missing metric: {metric}")
            return False
    
    # Check for specific reject reasons
    reject_reasons = ["size", "count", "shape"]
    for reason in reject_reasons:
        if f'reason="{reason}"' in metrics_text:
            print(f"✅ Found reject reason: {reason}")
        else:
            print(f"❌ Missing reject reason: {reason}")
            return False
    
    print("✅ Metrics verification passed")
    return True

def main():
    """Run all tests"""
    print("Starting Ingest Limits Tests")
    print("=" * 50)
    
    tests = [
        test_size_limit_gzip,
        test_record_count_limit,
        test_batch_shape_invalid,
        test_valid_batch,
        test_metrics
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False

if __name__ == "__main__":
    main()
