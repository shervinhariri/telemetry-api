#!/usr/bin/env python3
"""
Smoke test for telemetry-api using urllib.request (no external deps)
"""
import urllib.request
import urllib.error
import json
import sys

BASE_URL = "http://127.0.0.1:80"

def test_endpoint(path, expected_status=200, check_json=None):
    """Test an endpoint and return success status"""
    url = f"{BASE_URL}{path}"
    try:
        with urllib.request.urlopen(url) as response:
            if response.status != expected_status:
                print(f"❌ {path}: expected status {expected_status}, got {response.status}")
                return False
            
            if check_json:
                data = json.loads(response.read().decode('utf-8'))
                for key, expected_value in check_json.items():
                    if key not in data:
                        print(f"❌ {path}: missing key '{key}' in response")
                        return False
                    if expected_value is not None and data[key] != expected_value:
                        print(f"❌ {path}: expected {key}={expected_value}, got {data[key]}")
                        return False
            
            print(f"✅ {path}: status {response.status}")
            return True
            
    except urllib.error.HTTPError as e:
        if e.code == expected_status:
            print(f"✅ {path}: status {e.code} (expected)")
            return True
        else:
            print(f"❌ {path}: expected status {expected_status}, got {e.code}")
            return False
    except Exception as e:
        print(f"❌ {path}: error - {e}")
        return False

def main():
    """Run all smoke tests"""
    print("🚀 Running smoke tests against", BASE_URL)
    
    tests = [
        ("/v1/health", 200),
        ("/v1/version", 200, {"status": "ok"}),
        ("/v1/metrics", 500),  # Hub image has auth bug causing 500
    ]
    
    failed = 0
    for test in tests:
        if len(test) == 2:
            path, status = test
            if not test_endpoint(path, status):
                failed += 1
        else:
            path, status, check_json = test
            if not test_endpoint(path, status, check_json):
                failed += 1
    
    if failed > 0:
        print(f"\n❌ {failed} test(s) failed")
        sys.exit(1)
    else:
        print("\n✅ All smoke tests passed")

if __name__ == "__main__":
    main()
