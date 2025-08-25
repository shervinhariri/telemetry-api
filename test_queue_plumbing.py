#!/usr/bin/env python3
"""
Test script for Queue/Worker Plumbing feature implementation
Verifies all requirements from Step 3 execution plan
"""

import os
import json
import time
import requests
import threading
import concurrent.futures

# Test configuration
BASE_URL = "http://localhost"
API_KEY = "seed-7db78993"  # Use a seeded key from the logs

def test_backpressure():
    """Test 1: Queue backpressure with small queue"""
    print("=== Test 1: Queue backpressure ===")
    
    # Create a small batch of records
    records = [{"id": i, "src_ip": f"1.1.1.{i%200}", "dst_ip": f"8.8.8.{i%200}"} for i in range(10)]
    payload = {
        "collector_id": "test_collector",
        "format": "flows.v1",
        "records": records
    }
    
    data = json.dumps(payload).encode()
    print(f"Created payload with {len(records)} records: {len(data)} bytes")
    
    # Send many requests in parallel to saturate the queue
    def send_request():
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {API_KEY}'
        }
        response = requests.post(f"{BASE_URL}/v1/ingest", data=data, headers=headers)
        return response.status_code, response.text
    
    # Send 50 requests in parallel (should saturate a small queue)
    print("Sending 50 parallel requests to saturate queue...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_request) for _ in range(50)]
        results = [future.result() for future in futures]
    
    # Count responses
    status_200 = sum(1 for status, _ in results if status == 200)
    status_503 = sum(1 for status, _ in results if status == 503)
    
    print(f"Results: 200 responses: {status_200}, 503 responses: {status_503}")
    
    # Check for 503 responses with proper headers and body
    backpressure_responses = [(status, text) for status, text in results if status == 503]
    
    if backpressure_responses:
        print("✅ Backpressure test passed - received 503 responses")
        # Check the first 503 response for proper format
        status, text = backpressure_responses[0]
        try:
            error_data = json.loads(text)
            assert error_data["error"] == "backpressure"
            assert "retry_after" in error_data
            print("✅ 503 response has correct JSON format")
        except Exception as e:
            print(f"❌ 503 response format error: {e}")
            return False
    else:
        print("❌ No backpressure detected - queue may be too large")
        return False
    
    return True

def test_worker_resilience():
    """Test 2: Worker resilience with bad records"""
    print("\n=== Test 2: Worker resilience ===")
    
    # Create a batch with one intentionally bad record
    records = [
        {"id": 1, "src_ip": "1.1.1.1", "dst_ip": "8.8.8.8"},  # Good record
        {"id": 2, "src_ip": "invalid-ip", "dst_ip": "8.8.8.8"},  # Bad record (invalid IP)
        {"id": 3, "src_ip": "1.1.1.3", "dst_ip": "8.8.8.8"},  # Good record
    ]
    
    payload = {
        "collector_id": "test_collector",
        "format": "flows.v1",
        "records": records
    }
    
    data = json.dumps(payload).encode()
    print(f"Created payload with {len(records)} records (including 1 bad record)")
    
    # Send the request
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'
    }
    
    response = requests.post(f"{BASE_URL}/v1/ingest", data=data, headers=headers)
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    
    # Should get 200 (batch accepted) even with bad record
    if response.status_code == 200:
        print("✅ Worker resilience test passed - batch accepted despite bad record")
        return True
    else:
        print(f"❌ Worker resilience test failed - got {response.status_code}")
        return False

def test_metrics():
    """Test 3: Check queue and worker metrics"""
    print("\n=== Test 3: Metrics verification ===")
    
    # Get metrics
    response = requests.get(f"{BASE_URL}/v1/metrics/prometheus")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    metrics_text = response.text
    
    # Check for queue metrics
    queue_metrics = [
        "telemetry_queue_depth",
        "telemetry_queue_saturation", 
        "telemetry_queue_enqueues_total",
        "telemetry_queue_drops_total"
    ]
    
    for metric in queue_metrics:
        if metric in metrics_text:
            print(f"✅ Found queue metric: {metric}")
        else:
            print(f"❌ Missing queue metric: {metric}")
            return False
    
    # Check for worker metrics
    worker_metrics = [
        "telemetry_worker_processed_total",
        "telemetry_worker_errors_total",
        "telemetry_event_processing_seconds"
    ]
    
    for metric in worker_metrics:
        if metric in metrics_text:
            print(f"✅ Found worker metric: {metric}")
        else:
            print(f"❌ Missing worker metric: {metric}")
            return False
    
    print("✅ Metrics verification passed")
    return True

def test_system_endpoint():
    """Test 4: Check /v1/system includes queue information"""
    print("\n=== Test 4: System endpoint queue info ===")
    
    # Get system info
    headers = {
        'Authorization': f'Bearer {API_KEY}'
    }
    
    response = requests.get(f"{BASE_URL}/v1/system", headers=headers)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    system_data = response.json()
    print(f"System response: {json.dumps(system_data, indent=2)}")
    
    # Check for queue information
    if "queue" in system_data:
        queue_info = system_data["queue"]
        required_fields = ["depth", "max", "saturation"]
        
        for field in required_fields:
            if field in queue_info:
                print(f"✅ Found queue field: {field} = {queue_info[field]}")
            else:
                print(f"❌ Missing queue field: {field}")
                return False
        
        print("✅ System endpoint queue info test passed")
        return True
    else:
        print("❌ No queue information in system endpoint")
        return False

def test_latency_metrics():
    """Test 5: Check that latency metrics are observed"""
    print("\n=== Test 5: Latency metrics ===")
    
    # Send a valid batch
    records = [{"id": i, "src_ip": f"1.1.1.{i%200}", "dst_ip": f"8.8.8.{i%200}"} for i in range(5)]
    payload = {
        "collector_id": "test_collector",
        "format": "flows.v1",
        "records": records
    }
    
    data = json.dumps(payload).encode()
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'
    }
    
    response = requests.post(f"{BASE_URL}/v1/ingest", data=data, headers=headers)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    # Wait a moment for processing
    time.sleep(2)
    
    # Check metrics for latency observations
    metrics_response = requests.get(f"{BASE_URL}/v1/metrics/prometheus")
    metrics_text = metrics_response.text
    
    # Look for latency metrics
    latency_metrics = [
        "telemetry_event_processing_seconds",
        "telemetry_stage_seconds"
    ]
    
    for metric in latency_metrics:
        if metric in metrics_text:
            print(f"✅ Found latency metric: {metric}")
        else:
            print(f"❌ Missing latency metric: {metric}")
            return False
    
    print("✅ Latency metrics test passed")
    return True

def main():
    """Run all tests"""
    print("Starting Queue/Worker Plumbing Tests")
    print("=" * 50)
    
    tests = [
        test_backpressure,
        test_worker_resilience,
        test_metrics,
        test_system_endpoint,
        test_latency_metrics
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
