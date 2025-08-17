#!/usr/bin/env python3
"""
Test script for the new structured logging system.
Demonstrates different logging configurations and outputs.
"""

import os
import sys
import time
import requests
import json
from typing import Dict, Any

def test_logging_configurations():
    """Test different logging configurations"""
    
    base_url = "http://localhost"
    
    # Test configurations
    configs = [
        {
            "name": "Development Mode (Text)",
            "env": {
                "ENVIRONMENT": "development",
                "LOG_LEVEL": "INFO",
                "LOG_FORMAT": "text",
                "HTTP_LOG_ENABLED": "true",
                "HTTP_LOG_SAMPLE_RATE": "1.0",
                "HTTP_LOG_EXCLUDE_PATHS": "/health"
            }
        },
        {
            "name": "Production Mode (JSON)",
            "env": {
                "ENVIRONMENT": "production",
                "LOG_LEVEL": "WARNING",
                "LOG_FORMAT": "json",
                "HTTP_LOG_ENABLED": "true",
                "HTTP_LOG_SAMPLE_RATE": "0.01",
                "HTTP_LOG_EXCLUDE_PATHS": "/health,/metrics,/system"
            }
        },
        {
            "name": "High-Volume Production",
            "env": {
                "ENVIRONMENT": "production",
                "LOG_LEVEL": "ERROR",
                "LOG_FORMAT": "json",
                "HTTP_LOG_ENABLED": "true",
                "HTTP_LOG_SAMPLE_RATE": "0.001",
                "HTTP_LOG_EXCLUDE_PATHS": "/health,/metrics,/system,/v1/version"
            }
        }
    ]
    
    print("🧪 Testing Structured Logging System")
    print("=" * 50)
    
    for config in configs:
        print(f"\n📋 Testing: {config['name']}")
        print("-" * 30)
        
        # Set environment variables
        for key, value in config['env'].items():
            os.environ[key] = value
            print(f"  {key}={value}")
        
        # Test API endpoints
        test_endpoints = [
            ("GET", "/v1/health", "Health check"),
            ("GET", "/v1/metrics", "Metrics endpoint"),
            ("GET", "/v1/system", "System info"),
            ("POST", "/v1/ingest", "Ingest endpoint (will fail without auth)"),
        ]
        
        for method, endpoint, description in test_endpoints:
            try:
                print(f"\n  🔍 Testing {method} {endpoint} ({description})")
                
                if method == "GET":
                    response = requests.get(f"{base_url}{endpoint}", timeout=5)
                else:
                    # POST with minimal data
                    response = requests.post(
                        f"{base_url}{endpoint}",
                        json={"records": []},
                        headers={"Authorization": "Bearer test-key"},
                        timeout=5
                    )
                
                print(f"    Status: {response.status_code}")
                print(f"    Trace ID: {response.headers.get('X-Trace-Id', 'N/A')}")
                
                # Check if response has structured data
                if response.headers.get('content-type', '').startswith('application/json'):
                    try:
                        data = response.json()
                        if isinstance(data, dict) and len(data) > 0:
                            print(f"    Response keys: {list(data.keys())}")
                    except:
                        pass
                
            except requests.exceptions.RequestException as e:
                print(f"    ❌ Error: {e}")
        
        print(f"\n  ✅ Configuration test completed")
    
    print(f"\n🎉 All logging configuration tests completed!")
    print(f"\n📖 Check the logs to see the different output formats:")
    print(f"   - Development: Human-readable with emojis")
    print(f"   - Production: JSON-structured for parsing")
    print(f"   - Sampling: Only 1% of successful requests logged in production")

def test_sampling_behavior():
    """Test the sampling behavior of HTTP request logging"""
    
    print(f"\n🎯 Testing HTTP Request Sampling")
    print("=" * 40)
    
    base_url = "http://localhost"
    
    # Test with different sample rates
    sample_rates = [1.0, 0.1, 0.01, 0.001]
    
    for rate in sample_rates:
        print(f"\n📊 Testing sample rate: {rate} ({rate*100}%)")
        
        # Make 100 requests to see sampling in action
        successful_requests = 0
        failed_requests = 0
        
        for i in range(100):
            try:
                response = requests.get(f"{base_url}/v1/health", timeout=1)
                if response.status_code < 400:
                    successful_requests += 1
                else:
                    failed_requests += 1
            except:
                failed_requests += 1
        
        print(f"  Requests: {successful_requests} successful, {failed_requests} failed")
        print(f"  Expected logged: ~{int(successful_requests * rate)} successful requests")
        print(f"  All failed requests should be logged regardless of sampling")

def main():
    """Main test function"""
    
    print("🚀 Telemetry API Structured Logging Test")
    print("=" * 50)
    
    # Check if API is running
    try:
        response = requests.get("http://localhost/v1/health", timeout=5)
        if response.status_code != 200:
            print("❌ API is not responding correctly")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ API is not running. Please start the API first:")
        print("   docker-compose up -d")
        sys.exit(1)
    
    print("✅ API is running and responding")
    
    # Run tests
    test_logging_configurations()
    test_sampling_behavior()
    
    print(f"\n📝 Next Steps:")
    print(f"   1. Check the logs to see structured output")
    print(f"   2. Try different environment variables")
    print(f"   3. Use docker-compose -f docker-compose.prod.yml up for production config")
    print(f"   4. See docs/LOGGING.md for full documentation")

if __name__ == "__main__":
    main()
