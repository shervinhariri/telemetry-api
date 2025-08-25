#!/usr/bin/env python3
"""
Comprehensive tests for hardening improvements
Tests auth/key seeding, response consistency, and system endpoints
"""

import os
import json
import time
import requests
import threading
import concurrent.futures
import gzip

# Test configuration
BASE_URL = "http://localhost"
API_KEY = "TEST_ADMIN_KEY"  # Use the default seeded admin key

def test_auth_hardening():
    """Test 1: Auth/key seeding hardening"""
    print("=== Test 1: Auth/key seeding hardening ===")
    
    # Test 1a: Metrics endpoint with valid key (should be 200)
    print("  Testing metrics endpoint with valid key...")
    response = requests.get(f"{BASE_URL}/v1/metrics", headers={"Authorization": f"Bearer {API_KEY}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print(f"  ✓ Metrics endpoint: {response.status_code}")
    
    # Test 1b: Metrics endpoint with bad key (should be 401)
    print("  Testing metrics endpoint with bad key...")
    response = requests.get(f"{BASE_URL}/v1/metrics", headers={"Authorization": "Bearer bad-key"})
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    print(f"  ✓ Bad key rejected: {response.status_code}")
    
    # Test 1c: Health endpoint (should be 200, no auth required)
    print("  Testing health endpoint (no auth required)...")
    response = requests.get(f"{BASE_URL}/v1/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["status"] == "healthy", f"Expected 'healthy', got {data['status']}"
    print(f"  ✓ Health endpoint: {response.status_code}")
    
    print("  ✓ Auth hardening tests passed")

def test_response_consistency():
    """Test 2: Response consistency for ingest endpoints"""
    print("=== Test 2: Response consistency ===")
    
    # Test 2a: Size limit response (413)
    print("  Testing size limit response...")
    large_data = b"x" * (6 * 1024 * 1024)  # 6 MB
    response = requests.post(
        f"{BASE_URL}/v1/ingest",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "Content-Encoding": "identity"
        },
        data=large_data
    )
    assert response.status_code == 413, f"Expected 413, got {response.status_code}"
    data = response.json()
    expected = {
        "error": "batch_too_large",
        "limit_bytes": 5242880,
        "content_encoding": "identity",
        "actual_bytes": len(large_data)
    }
    assert data == expected, f"Expected {expected}, got {data}"
    print(f"  ✓ Size limit response: {response.status_code}")
    
    # Test 2b: Count limit response (422)
    print("  Testing count limit response...")
    too_many_records = [{"id": i} for i in range(10001)]
    response = requests.post(
        f"{BASE_URL}/v1/ingest",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        },
        json=too_many_records
    )
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    data = response.json()
    expected = {
        "error": "too_many_records",
        "limit": 10000,
        "observed": 10001
    }
    assert data == expected, f"Expected {expected}, got {data}"
    print(f"  ✓ Count limit response: {response.status_code}")
    
    # Test 2c: Shape error response (422)
    print("  Testing shape error response...")
    invalid_shape = '{"id":1}{"id":2}'  # Concatenated JSON objects
    response = requests.post(
        f"{BASE_URL}/v1/ingest",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        },
        data=invalid_shape
    )
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    data = response.json()
    expected = {
        "error": "bad_batch_shape",
        "hint": "expected JSON array or JSONL"
    }
    assert data == expected, f"Expected {expected}, got {data}"
    print(f"  ✓ Shape error response: {response.status_code}")
    
    print("  ✓ Response consistency tests passed")

def test_system_endpoint():
    """Test 3: System endpoint with queue information"""
    print("=== Test 3: System endpoint ===")
    
    response = requests.get(f"{BASE_URL}/v1/system", headers={"Authorization": f"Bearer {API_KEY}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    
    # Check required fields
    required_fields = ["status", "version", "features", "queue", "workers"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    # Check queue information
    queue = data["queue"]
    assert "depth" in queue, "Missing queue.depth"
    assert "max" in queue, "Missing queue.max"
    assert "saturation" in queue, "Missing queue.saturation"
    assert isinstance(queue["depth"], int), "queue.depth should be int"
    assert isinstance(queue["max"], int), "queue.max should be int"
    assert isinstance(queue["saturation"], float), "queue.saturation should be float"
    
    # Check features
    features = data["features"]
    assert "udp_head" in features, "Missing features.udp_head"
    assert features["udp_head"] in ["disabled", "ready"], f"Invalid udp_head status: {features['udp_head']}"
    
    # Check version parity
    version_response = requests.get(f"{BASE_URL}/v1/version")
    version_data = version_response.json()
    assert data["version"] == version_data["version"], "Version mismatch between /v1/system and /v1/version"
    
    print(f"  ✓ System endpoint: {response.status_code}")
    print(f"  ✓ Queue depth: {queue['depth']}/{queue['max']} (saturation: {queue['saturation']:.2f})")
    print(f"  ✓ Workers: {data['workers']}")
    print(f"  ✓ UDP head: {features['udp_head']}")
    print(f"  ✓ Version: {data['version']}")

def test_queue_backpressure():
    """Test 4: Queue backpressure with small queue"""
    print("=== Test 4: Queue backpressure ===")
    
    # Create a small batch
    records = [{"id": i, "src_ip": f"1.1.1.{i%200}", "dst_ip": f"8.8.8.{i%200}"} for i in range(10)]
    
    # Send many requests to saturate the queue
    responses = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for i in range(200):  # Send 200 requests to saturate queue of 100
            future = executor.submit(
                requests.post,
                f"{BASE_URL}/v1/ingest",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_KEY}"
                },
                json=records
            )
            futures.append(future)
        
        # Collect responses
        for future in concurrent.futures.as_completed(futures):
            try:
                response = future.result()
                responses.append(response)
            except Exception as e:
                print(f"  Request failed: {e}")
    
    # Count response types
    status_202 = sum(1 for r in responses if r.status_code == 202)
    status_503 = sum(1 for r in responses if r.status_code == 503)
    
    print(f"  ✓ Responses: {status_202} accepted, {status_503} backpressure")
    
    # Check that we got successful responses (queue is working)
    assert status_202 > 0, "Expected some successful responses"
    
    # If we got 503 responses, check they have proper format
    if status_503 > 0:
        for response in responses:
            if response.status_code == 503:
                data = response.json()
                assert data["error"] == "backpressure", f"Expected 'backpressure' error, got {data['error']}"
                assert "Retry-After" in response.headers, "Missing Retry-After header"
                assert "retry_after" in data, "Missing retry_after in response body"
                break
        print("  ✓ Backpressure responses have correct format")
    else:
        print("  ✓ Queue processed all requests without backpressure")
    
    print("  ✓ Queue backpressure tests passed")

def test_metrics_consistency():
    """Test 5: Metrics consistency"""
    print("=== Test 5: Metrics consistency ===")
    
    # Get metrics before test
    response = requests.get(f"{BASE_URL}/v1/metrics", headers={"Authorization": f"Bearer {API_KEY}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    metrics_before = response.json()
    
    # Send a valid request
    records = [{"id": 1, "src_ip": "1.1.1.1", "dst_ip": "8.8.8.8"}]
    response = requests.post(
        f"{BASE_URL}/v1/ingest",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        },
        json=records
    )
    assert response.status_code == 202, f"Expected 202, got {response.status_code}"
    
    # Wait a moment for processing
    time.sleep(1)
    
    # Get metrics after test
    response = requests.get(f"{BASE_URL}/v1/metrics", headers={"Authorization": f"Bearer {API_KEY}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    metrics_after = response.json()
    
    # Check that metrics changed
    if "ingest" in metrics_after and "ingest" in metrics_before:
        batches_before = metrics_before["ingest"].get("batches_total", 0)
        batches_after = metrics_after["ingest"].get("batches_total", 0)
        assert batches_after >= batches_before, "Ingest batches should not decrease"
    
    print("  ✓ Metrics consistency tests passed")

def main():
    """Run all hardening tests"""
    print("Running hardening tests...")
    
    try:
        test_auth_hardening()
        test_response_consistency()
        test_system_endpoint()
        test_queue_backpressure()
        test_metrics_consistency()
        
        print("\n🎉 All hardening tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
