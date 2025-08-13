#!/usr/bin/env python3
"""
Test Script for Patch 5.1 - Version Management & Output Connectors
Demonstrates all the new features and endpoints.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8080"
API_KEY = "TEST_KEY"

def test_version_endpoint():
    """Test the version endpoint"""
    print("🔍 Testing /v1/version endpoint...")
    response = requests.get(f"{BASE_URL}/v1/version")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Version: {data['service']} {data['version']} • {data['git_sha']}")
        print(f"   Image: {data['image']}:{data['image_tag']}")
        return data
    else:
        print(f"❌ Failed: {response.status_code}")
        return None

def test_updates_check():
    """Test the updates check endpoint"""
    print("\n🔍 Testing /v1/updates/check endpoint...")
    response = requests.get(f"{BASE_URL}/v1/updates/check")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Update check: enabled={data['enabled']}")
        print(f"   Current: {data['current']}, Latest: {data['latest']}")
        print(f"   Update available: {data['update_available']}")
        return data
    else:
        print(f"❌ Failed: {response.status_code}")
        return None

def test_splunk_config():
    """Test Splunk HEC configuration"""
    print("\n🔍 Testing /v1/outputs/splunk endpoint...")
    
    # Test POST
    config = {
        "hec_url": "https://splunk.example:8088/services/collector",
        "token": "test-token-123",
        "index": "telemetry",
        "sourcetype": "telemetry:event",
        "batch_size": 500,
        "max_retries": 3
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(f"{BASE_URL}/v1/outputs/splunk", 
                           headers=headers, json=config)
    if response.status_code == 200:
        print("✅ Splunk config saved successfully")
        
        # Test GET
        response = requests.get(f"{BASE_URL}/v1/outputs/splunk", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"   Retrieved config: {data['splunk']['hec_url']}")
            return True
    else:
        print(f"❌ Failed: {response.status_code}")
        return False

def test_elastic_config():
    """Test Elasticsearch configuration"""
    print("\n🔍 Testing /v1/outputs/elastic endpoint...")
    
    # Test POST
    config = {
        "urls": ["https://es1:9200", "https://es2:9200"],
        "index_prefix": "telemetry-",
        "bulk_size": 1000,
        "max_retries": 5,
        "pipeline": "telemetry-pipeline"
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(f"{BASE_URL}/v1/outputs/elastic", 
                           headers=headers, json=config)
    if response.status_code == 200:
        print("✅ Elasticsearch config saved successfully")
        
        # Test GET
        response = requests.get(f"{BASE_URL}/v1/outputs/elastic", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"   Retrieved config: {len(data['elastic']['urls'])} nodes")
            return True
    else:
        print(f"❌ Failed: {response.status_code}")
        return False

def test_admin_update():
    """Test admin update endpoint (dev-only)"""
    print("\n🔍 Testing /v1/admin/update endpoint...")
    
    headers = {"X-Admin-Token": "dev-only-token"}
    response = requests.post(f"{BASE_URL}/v1/admin/update", headers=headers)
    
    # This will likely fail in containerized environment (no Docker CLI)
    if response.status_code == 200:
        print("✅ Admin update successful")
        return True
    else:
        print(f"⚠️  Admin update failed (expected in container): {response.status_code}")
        print("   This is normal - Docker CLI not available in container")
        return False

def test_health_endpoint():
    """Test that health endpoint remains public"""
    print("\n🔍 Testing /v1/health endpoint (should be public)...")
    response = requests.get(f"{BASE_URL}/v1/health")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Health check: {data['status']} - {data['service']}")
        return True
    else:
        print(f"❌ Failed: {response.status_code}")
        return False

def main():
    """Run all Patch 5.1 tests"""
    print("🚀 Patch 5.1 - Version Management & Output Connectors Test")
    print("=" * 60)
    
    # Test all endpoints
    version_data = test_version_endpoint()
    updates_data = test_updates_check()
    splunk_ok = test_splunk_config()
    elastic_ok = test_elastic_config()
    admin_ok = test_admin_update()
    health_ok = test_health_endpoint()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"   Version endpoint: {'✅' if version_data else '❌'}")
    print(f"   Updates check: {'✅' if updates_data else '❌'}")
    print(f"   Splunk config: {'✅' if splunk_ok else '❌'}")
    print(f"   Elastic config: {'✅' if elastic_ok else '❌'}")
    print(f"   Admin update: {'✅' if admin_ok else '⚠️'}")
    print(f"   Health endpoint: {'✅' if health_ok else '❌'}")
    
    if version_data and updates_data:
        print(f"\n🎯 Current version: {version_data['version']}")
        if updates_data['update_available']:
            print(f"🔄 Update available: {updates_data['latest']}")
        else:
            print("✅ Up to date!")
    
    print("\n🌐 GUI available at: http://localhost:8080")
    print("   Look for the version badge in the top-right corner!")

if __name__ == "__main__":
    main()
