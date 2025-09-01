"""
E2E smoke tests for P1 features (v0.8.10+)

Tests:
- GET /v1/system includes geo and udp_head
- POST /v1/geo/download returns job_id
- GET /v1/jobs shows the job
- POST /v1/outputs/test with no config returns structured error
- Invalid config returns 422 with {field, reason}
"""

import pytest
import requests
import json
import time
import os
from typing import Dict, Any


class TestP1Features:
    """E2E tests for P1 features"""
    
    @pytest.fixture
    def api_base(self) -> str:
        """API base URL - can be overridden for different environments"""
        return "http://localhost:8080"  # Dev container
    
    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        """Authentication headers"""
        # Use environment variables with fallbacks
        admin_key = os.getenv("TEST_API_KEY") or os.getenv("DEV_ADMIN_KEY") or "DEV_ADMIN_KEY_5a8f9ffdc3"
        return {
            "Authorization": f"Bearer {admin_key}",
            "Content-Type": "application/json"
        }
    
    def test_system_endpoint_includes_geo_and_udp_head(self, api_base: str, auth_headers: Dict[str, str]):
        """Test that GET /v1/system includes geo and udp_head blocks"""
        response = requests.get(f"{api_base}/v1/system", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check geo block exists
        assert "geo" in data, "System response missing 'geo' block"
        geo = data["geo"]
        assert isinstance(geo, dict), "Geo block should be a dictionary"
        assert "enabled" in geo, "Geo block missing 'enabled' field"
        assert "vendor" in geo, "Geo block missing 'vendor' field"
        assert "database" in geo, "Geo block missing 'database' field"
        assert "status" in geo, "Geo block missing 'status' field"
        
        # Check udp_head block exists
        assert "udp_head" in data, "System response missing 'udp_head' block"
        udp_head = data["udp_head"]
        assert isinstance(udp_head, str), "UDP head should be a string status"
        assert udp_head in ["ready", "stopped", "error"], f"Invalid UDP head status: {udp_head}"
    
    def test_geo_download_creates_job(self, api_base: str, auth_headers: Dict[str, str]):
        """Test that POST /v1/geo/download creates a job and it appears in GET /v1/jobs"""
        # Start geo download
        response = requests.post(f"{api_base}/v1/geo/download", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "job_id" in data, "Geo download response missing 'job_id'"
        job_id = data["job_id"]
        assert isinstance(job_id, str), "Job ID should be a string"
        assert len(job_id) > 0, "Job ID should not be empty"
        
        # Wait a moment for job to be created
        time.sleep(1)
        
        # Check job appears in jobs list
        response = requests.get(f"{api_base}/v1/jobs", headers=auth_headers)
        assert response.status_code == 200
        
        jobs = response.json()
        assert isinstance(jobs, list), "Jobs response should be a list"
        
        # Find our job
        job_found = False
        for job in jobs:
            if job.get("id") == job_id:
                job_found = True
                assert job.get("type") == "geo_download", f"Job type should be 'geo_download', got {job.get('type')}"
                assert "status" in job, "Job missing 'status' field"
                assert "created_at" in job, "Job missing 'created_at' field"
                break
        
        assert job_found, f"Job {job_id} not found in jobs list"
    
    def test_outputs_test_without_config(self, api_base: str, auth_headers: Dict[str, str]):
        """Test that POST /v1/outputs/test with no config returns structured error (not 500)"""
        # Test Splunk without config
        response = requests.post(
            f"{api_base}/v1/outputs/test",
            headers=auth_headers,
            json={"target": "splunk"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "target" in data, "Response missing 'target' field"
        assert data["target"] == "splunk", f"Target should be 'splunk', got {data['target']}"
        assert "error" in data, "Response missing 'error' field"
        assert data["error"] is not None, "Error should not be null"
        assert "http_status" in data, "Response missing 'http_status' field"
        assert "duration_ms" in data, "Response missing 'duration_ms' field"
        assert "bytes" in data, "Response missing 'bytes' field"
        assert "request_id" in data, "Response missing 'request_id' field"
        
        # Test Elastic without config
        response = requests.post(
            f"{api_base}/v1/outputs/test",
            headers=auth_headers,
            json={"target": "elastic"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["target"] == "elastic", f"Target should be 'elastic', got {data['target']}"
        assert data["error"] is not None, "Error should not be null"
    
    def test_outputs_validation_missing_splunk_token(self, api_base: str, auth_headers: Dict[str, str]):
        """Test that PUT /v1/outputs/splunk with missing token returns 422 with {field, reason}"""
        response = requests.put(
            f"{api_base}/v1/outputs/splunk",
            headers=auth_headers,
            json={"url": "https://splunk.example:8088"}
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "422 response missing 'detail' field"
        assert isinstance(data["detail"], list), "Detail should be a list"
        assert len(data["detail"]) > 0, "Detail should not be empty"
        
        # Check for token validation error
        token_error_found = False
        for error in data["detail"]:
            if "token" in str(error).lower():
                token_error_found = True
                break
        
        assert token_error_found, "No token validation error found in response"
    
    def test_outputs_validation_bad_elastic_url(self, api_base: str, auth_headers: Dict[str, str]):
        """Test that PUT /v1/outputs/elastic with bad URL returns 422 with {field, reason}"""
        response = requests.put(
            f"{api_base}/v1/outputs/elastic",
            headers=auth_headers,
            json={"url": "invalid-url", "index": "telemetry-*"}
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "422 response missing 'detail' field"
        assert isinstance(data["detail"], list), "Detail should be a list"
        assert len(data["detail"]) > 0, "Detail should not be empty"
        
        # Check for URL validation error
        url_error_found = False
        for error in data["detail"]:
            if "url" in str(error).lower() or "http" in str(error).lower():
                url_error_found = True
                break
        
        assert url_error_found, "No URL validation error found in response"
    
    def test_outputs_test_invalid_target(self, api_base: str, auth_headers: Dict[str, str]):
        """Test that POST /v1/outputs/test with invalid target returns 422"""
        response = requests.post(
            f"{api_base}/v1/outputs/test",
            headers=auth_headers,
            json={"target": "invalid"}
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        
        data = response.json()
        assert "status" in data, "422 response missing 'status' field"
        assert data["status"] == "error", f"Status should be 'error', got {data['status']}"
        assert "field" in data, "422 response missing 'field' field"
        assert "reason" in data, "422 response missing 'reason' field"
        assert data["field"] == "target", f"Field should be 'target', got {data['field']}"
    
    def test_metrics_include_output_test_counters(self, api_base: str, auth_headers: Dict[str, str]):
        """Test that /v1/metrics includes output test counters"""
        response = requests.get(f"{api_base}/v1/metrics", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check for output test metrics
        assert "outputs_test_success_total" in data, "Metrics missing 'outputs_test_success_total'"
        assert "outputs_test_fail_total" in data, "Metrics missing 'outputs_test_fail_total'"
        
        # Check structure
        success_metrics = data["outputs_test_success_total"]
        fail_metrics = data["outputs_test_fail_total"]
        
        assert isinstance(success_metrics, dict), "outputs_test_success_total should be a dict"
        assert isinstance(fail_metrics, dict), "outputs_test_fail_total should be a dict"
        
        # Check for expected targets
        assert "splunk" in success_metrics, "Success metrics missing 'splunk'"
        assert "elastic" in success_metrics, "Success metrics missing 'elastic'"
        assert "splunk" in fail_metrics, "Fail metrics missing 'splunk'"
        assert "elastic" in fail_metrics, "Fail metrics missing 'elastic'"
        
        # Values should be integers
        for target in ["splunk", "elastic"]:
            assert isinstance(success_metrics[target], int), f"Success metric for {target} should be int"
            assert isinstance(fail_metrics[target], int), f"Fail metric for {target} should be int"
    
    def test_udp_head_metrics_exist(self, api_base: str, auth_headers: Dict[str, str]):
        """Test that /v1/metrics includes UDP head metrics"""
        response = requests.get(f"{api_base}/v1/metrics", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check for UDP head metrics
        assert "udp_head_packets_total" in data, "Metrics missing 'udp_head_packets_total'"
        assert "udp_head_bytes_total" in data, "Metrics missing 'udp_head_bytes_total'"
        assert "udp_head_last_packet_ts" in data, "Metrics missing 'udp_head_last_packet_ts'"
        
        # Check types
        assert isinstance(data["udp_head_packets_total"], int), "udp_head_packets_total should be int"
        assert isinstance(data["udp_head_bytes_total"], int), "udp_head_bytes_total should be int"
        assert isinstance(data["udp_head_last_packet_ts"], (int, float)), "udp_head_last_packet_ts should be numeric"
