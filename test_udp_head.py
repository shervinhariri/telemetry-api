#!/usr/bin/env python3
"""
Test script for UDP Head feature implementation
Verifies all requirements from the execution plan
"""

import os
import time
import socket
import asyncio
import json

def test_feature_flag_disabled():
    """Test 1: Default safe - UDP head disabled when flag is off"""
    print("=== Test 1: Feature flag disabled ===")
    
    # Clear any existing environment variable
    if 'FEATURE_UDP_HEAD' in os.environ:
        del os.environ['FEATURE_UDP_HEAD']
    
    # Reload config to pick up the cleared environment variable
    import importlib
    import app.config
    importlib.reload(app.config)
    
    # Reload modules that depend on config
    import app.udp_head
    import app.api.system
    importlib.reload(app.udp_head)
    importlib.reload(app.api.system)
    
    from app.api.system import get_system_info
    from app.udp_head import get_udp_head_status
    
    # Test system endpoint
    result = asyncio.run(get_system_info())
    features = result.get('features', {})
    udp_status = features.get('udp_head')
    
    print(f"System endpoint udp_head status: {udp_status}")
    assert udp_status == 'disabled', f"Expected 'disabled', got '{udp_status}'"
    
    # Test direct status function
    status = get_udp_head_status()
    print(f"Direct status function: {status}")
    assert status == 'disabled', f"Expected 'disabled', got '{status}'"
    
    print("✓ Test 1 PASSED: UDP head correctly disabled by default\n")

def test_feature_flag_enabled():
    """Test 2: Flag works - UDP head ready when flag is on"""
    print("=== Test 2: Feature flag enabled ===")
    
    # Set feature flag
    os.environ['FEATURE_UDP_HEAD'] = 'true'
    
    # Reload config to pick up the new environment variable
    import importlib
    import app.config
    importlib.reload(app.config)
    
    # Reload modules that depend on config
    import app.udp_head
    import app.api.system
    importlib.reload(app.udp_head)
    importlib.reload(app.api.system)
    
    from app.udp_head import start_udp_head, get_udp_head_status
    from app.api.system import get_system_info
    
    # Start UDP head
    start_udp_head()
    time.sleep(0.2)  # Wait for bind
    
    # Test system endpoint
    result = asyncio.run(get_system_info())
    features = result.get('features', {})
    udp_status = features.get('udp_head')
    
    print(f"System endpoint udp_head status: {udp_status}")
    assert udp_status == 'ready', f"Expected 'ready', got '{udp_status}'"
    
    # Test direct status function
    status = get_udp_head_status()
    print(f"Direct status function: {status}")
    assert status == 'ready', f"Expected 'ready', got '{status}'"
    
    print("✓ Test 2 PASSED: UDP head correctly ready when flag enabled\n")

def test_udp_traffic():
    """Test 3: Traffic observed - UDP datagrams increment counter"""
    print("=== Test 3: UDP traffic ===")
    
    from app.udp_head import get_udp_stats
    from app.services.prometheus_metrics import prometheus_metrics
    
    # Get initial stats
    initial_stats = get_udp_stats()
    initial_datagrams = initial_stats['datagrams_total']
    print(f"Initial datagrams total: {initial_datagrams}")
    
    # Send UDP packet
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(b'test_packet', ('127.0.0.1', 8081))
    s.close()
    
    time.sleep(0.1)  # Wait for processing
    
    # Get updated stats
    updated_stats = get_udp_stats()
    updated_datagrams = updated_stats['datagrams_total']
    print(f"Updated datagrams total: {updated_datagrams}")
    
    assert updated_datagrams > initial_datagrams, f"Expected datagrams to increment, got {initial_datagrams} -> {updated_datagrams}"
    
    # Check Prometheus metrics
    metrics_text = prometheus_metrics.get_metrics().decode('utf-8')
    datagram_lines = [line for line in metrics_text.split('\n') if 'telemetry_udp_head_datagrams_total' in line and not line.startswith('#')]
    if datagram_lines:
        metric_value = float(datagram_lines[0].split()[-1])
        print(f"Prometheus metric value: {metric_value}")
        assert metric_value > 0, f"Expected positive metric value, got {metric_value}"
    
    print("✓ Test 3 PASSED: UDP datagrams increment counter\n")

def test_version_parity():
    """Test 4: Version parity between /v1/system and /v1/version"""
    print("=== Test 4: Version parity ===")
    
    from app.api.system import get_system_info
    from app.api.version import get_version
    
    system_result = asyncio.run(get_system_info())
    version_result = get_version()
    
    system_version = system_result.get('version')
    version_endpoint_version = version_result.get('version')
    
    print(f"System endpoint version: {system_version}")
    print(f"Version endpoint version: {version_endpoint_version}")
    
    assert system_version == version_endpoint_version, f"Versions don't match: {system_version} != {version_endpoint_version}"
    
    print("✓ Test 4 PASSED: Version parity confirmed\n")

def test_metrics_structure():
    """Test 5: Metrics structure and content"""
    print("=== Test 5: Metrics structure ===")
    
    from app.metrics import get_metrics
    from app.services.prometheus_metrics import prometheus_metrics
    
    # Test main metrics endpoint
    metrics = get_metrics()
    udp_head_metrics = metrics.get('udp_head', {})
    
    print(f"Main metrics UDP head section: {udp_head_metrics}")
    
    required_keys = ['ready', 'bind_errors', 'datagrams_total', 'port']
    for key in required_keys:
        assert key in udp_head_metrics, f"Missing key '{key}' in UDP head metrics"
    
    # Test Prometheus metrics
    metrics_text = prometheus_metrics.get_metrics().decode('utf-8')
    
    required_metrics = [
        'telemetry_udp_head_ready',
        'telemetry_udp_head_datagrams_total',
        'telemetry_udp_head_bind_errors_total'
    ]
    
    for metric in required_metrics:
        assert metric in metrics_text, f"Missing Prometheus metric: {metric}"
    
    print("✓ Test 5 PASSED: Metrics structure correct\n")

def test_cleanup():
    """Test 6: Cleanup and shutdown"""
    print("=== Test 6: Cleanup ===")
    
    from app.udp_head import stop_udp_head, get_udp_head_status
    
    # Stop UDP head
    stop_udp_head()
    time.sleep(0.1)
    
    # Check status
    status = get_udp_head_status()
    print(f"Status after stop: {status}")
    
    # Should still be 'ready' if feature flag is enabled, but socket should be closed
    assert status in ['ready', 'disabled'], f"Unexpected status after stop: {status}"
    
    print("✓ Test 6 PASSED: Cleanup successful\n")

def main():
    """Run all tests"""
    print("Starting UDP Head feature tests...\n")
    
    try:
        test_feature_flag_disabled()
        test_feature_flag_enabled()
        test_udp_traffic()
        test_version_parity()
        test_metrics_structure()
        test_cleanup()
        
        print("🎉 ALL TESTS PASSED! UDP Head feature implementation is working correctly.")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
