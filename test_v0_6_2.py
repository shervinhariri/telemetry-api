#!/usr/bin/env python3
"""
Comprehensive test for v0.6.2 - Single Container with Fixed Metrics
"""

import requests
import time
import json
from datetime import datetime

def test_health():
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get("http://localhost/v1/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_version():
    print("🔍 Testing version endpoint...")
    try:
        response = requests.get("http://localhost/v1/version")
        if response.status_code == 200:
            version = response.json()
            print(f"✅ Version: {version.get('version', 'unknown')}")
            return version.get('version') == '0.6.2'
        else:
            print(f"❌ Version check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Version check error: {e}")
        return False

def test_metrics_before():
    print("🔍 Testing metrics before events...")
    try:
        response = requests.get("http://localhost/v1/metrics")
        if response.status_code == 200:
            metrics = response.json()
            totals = metrics.get('totals', {})
            print(f"  Events: {totals.get('events', 0)}")
            print(f"  Threat Matches: {totals.get('threat_matches', 0)}")
            print(f"  Risk Count: {totals.get('risk_count', 0)}")
            return metrics
        else:
            print(f"❌ Metrics failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Metrics error: {e}")
        return None

def test_enrichment():
    print("🔍 Testing enrichment...")
    test_lookup = {
        "ip": "45.149.3.100"
    }
    
    try:
        response = requests.post(
            "http://localhost/v1/lookup",
            headers={"Authorization": "Bearer TEST_KEY", "Content-Type": "application/json"},
            json=test_lookup
        )
        if response.status_code == 200:
            enriched = response.json()
            ti_matches = enriched.get('ti', {}).get('matches', [])
            risk_score = enriched.get('risk_score', 0)
            print(f"✅ Enrichment working: {len(ti_matches)} threats, risk={risk_score}")
            return len(ti_matches) > 0 and risk_score > 0
        else:
            print(f"❌ Enrichment failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Enrichment error: {e}")
        return False

def test_ingest_and_metrics():
    print("🔍 Testing ingest and metrics update...")
    
    # Send multiple events
    events = []
    for i in range(5):
        event = {
            "src_ip": f"45.149.3.{100 + i}",
            "dst_ip": "8.8.8.8",
            "src_port": 12345 + i,
            "dst_port": 80,
            "bytes": 1500 + i * 100,
            "proto": "tcp",
            "ts": int(time.time() * 1000) + i
        }
        events.append(event)
    
    try:
        response = requests.post(
            "http://localhost/v1/ingest",
            headers={"Authorization": "Bearer TEST_KEY", "Content-Type": "application/json"},
            json={"records": events}
        )
        if response.status_code == 200:
            print("✅ Events ingested successfully")
            
            # Wait for processing
            print("⏳ Waiting for processing...")
            time.sleep(5)
            
            # Check metrics
            metrics_response = requests.get("http://localhost/v1/metrics")
            if metrics_response.status_code == 200:
                metrics = metrics_response.json()
                totals = metrics.get('totals', {})
                
                print(f"📊 Updated Metrics:")
                print(f"  Events: {totals.get('events', 0)}")
                print(f"  Threat Matches: {totals.get('threat_matches', 0)}")
                print(f"  Risk Count: {totals.get('risk_count', 0)}")
                print(f"  Risk Sum: {totals.get('risk_sum', 0)}")
                
                if totals.get('threat_matches', 0) > 0:
                    print("✅ Threat detection working in metrics!")
                else:
                    print("❌ No threat matches in metrics")
                    
                if totals.get('risk_count', 0) > 0:
                    avg_risk = totals.get('risk_sum', 0) / totals.get('risk_count', 1)
                    print(f"✅ Risk scoring working! Avg: {avg_risk:.2f}")
                else:
                    print("❌ No risk scores in metrics")
                    
                return totals.get('threat_matches', 0) > 0 and totals.get('risk_count', 0) > 0
            else:
                print(f"❌ Metrics check failed: {metrics_response.status_code}")
                return False
        else:
            print(f"❌ Ingest failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ingest error: {e}")
        return False

def test_dashboard():
    print("🔍 Testing dashboard...")
    try:
        response = requests.get("http://localhost/")
        if response.status_code == 200:
            print("✅ Dashboard accessible")
            return True
        else:
            print(f"❌ Dashboard failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        return False

def test_performance():
    print("🔍 Testing performance with high-volume traffic...")
    
    # Send 50 events rapidly
    events = []
    for i in range(50):
        event = {
            "src_ip": f"192.168.1.{i % 254 + 1}",
            "dst_ip": "8.8.8.8",
            "src_port": 1024 + i,
            "dst_port": 80,
            "bytes": 1000 + i * 10,
            "proto": "tcp",
            "ts": int(time.time() * 1000) + i
        }
        events.append(event)
    
    start_time = time.time()
    try:
        response = requests.post(
            "http://localhost/v1/ingest",
            headers={"Authorization": "Bearer TEST_KEY", "Content-Type": "application/json"},
            json={"records": events}
        )
        end_time = time.time()
        
        if response.status_code == 200:
            print(f"✅ Performance test: {len(events)} events in {end_time - start_time:.2f}s")
            print(f"   Rate: {len(events) / (end_time - start_time):.1f} events/sec")
            
            # Wait and check final metrics
            time.sleep(3)
            metrics_response = requests.get("http://localhost/v1/metrics")
            if metrics_response.status_code == 200:
                metrics = metrics_response.json()
                totals = metrics.get('totals', {})
                print(f"📊 Final Metrics:")
                print(f"  Total Events: {totals.get('events', 0)}")
                print(f"  Total Threat Matches: {totals.get('threat_matches', 0)}")
                print(f"  Total Risk Count: {totals.get('risk_count', 0)}")
                
                rates = metrics.get('rates', {})
                print(f"  Events per minute: {rates.get('epm_1m', 0)}")
                
                return True
            else:
                print(f"❌ Final metrics failed: {metrics_response.status_code}")
                return False
        else:
            print(f"❌ Performance test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Performance test error: {e}")
        return False

def main():
    print("🚀 Starting v0.6.2 Comprehensive Test")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health),
        ("Version Check", test_version),
        ("Initial Metrics", test_metrics_before),
        ("Enrichment", test_enrichment),
        ("Ingest & Metrics", test_ingest_and_metrics),
        ("Dashboard", test_dashboard),
        ("Performance", test_performance)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        print("-" * 30)
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! v0.6.2 is working correctly!")
        print("\n🌐 Dashboard available at: http://localhost")
        print("📊 API available at: http://localhost/v1")
    else:
        print("⚠️  Some tests failed. Check the logs above.")
    
    return passed == total

if __name__ == "__main__":
    main()
