#!/usr/bin/env python3
"""
Unit and integration tests for Telemetry API
"""
import pytest
import json
import os
# Test data
API_KEY = "TEST_ADMIN_KEY"
VALID_HEADERS = {"Authorization": f"Bearer {API_KEY}"}

def test_health_endpoint(client):
    """Test health endpoint"""
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "telemetry-api"
    assert data["version"] == "v1"
    assert "X-API-Version" in response.headers

def test_version_endpoint(client):
    """Test version endpoint"""
    response = client.get("/v1/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "git_tag" in data
    assert "image_digest" in data
    assert "X-API-Version" in response.headers

def test_schema_endpoint(client):
    """Test schema endpoint"""
    response = client.get("/v1/schema")
    assert response.status_code == 200
    data = response.json()
    assert "enriched_schema" in data
    assert "input_schemas" in data
    assert "X-API-Version" in response.headers

def test_ingest_zeek_conn(client):
    """Test Zeek connection ingest"""
    payload = {
        "collector_id": "test-zeek-1",
        "format": "zeek.conn",
        "records": [
            {
                "ts": 1723351200.456,
                "id_orig_h": "10.1.2.3",
                "id_orig_p": 55342,
                "id_resp_h": "8.8.8.8",
                "id_resp_p": 53,
                "proto": "udp",
                "service": "dns",
                "duration": 0.025,
                "orig_bytes": 78,
                "resp_bytes": 256
            }
        ]
    }
    
    response = client.post("/v1/ingest", json=payload, headers=VALID_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["collector_id"] == "test-zeek-1"
    assert data["format"] == "zeek.conn"
    assert data["count"] == 1
    assert len(data["records"]) == 1
    
    record = data["records"][0]
    assert "risk_score" in record
    assert isinstance(record["risk_score"], int)
    assert 0 <= record["risk_score"] <= 100
    assert "threat" in record
    assert "reasons" in record
    assert "X-API-Version" in response.headers

def test_ingest_flows(client):
    """Test flows ingest"""
    payload = {
        "collector_id": "test-flows-1",
        "format": "flows.v1",
        "records": [
            {
                "ts": 1723351200.456,
                "src_ip": "192.168.1.100",
                "dst_ip": "1.1.1.1",
                "src_port": 12345,
                "dst_port": 80,
                "protocol": "tcp",
                "bytes": 1024,
                "packets": 10
            }
        ]
    }
    
    response = client.post("/v1/ingest", json=payload, headers=VALID_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "flows.v1"
    assert data["count"] == 1
    
    record = data["records"][0]
    assert "risk_score" in record
    assert isinstance(record["risk_score"], int)
    assert 0 <= record["risk_score"] <= 100

def test_lookup_endpoint(client):
    """Test IP lookup endpoint"""
    payload = {"ip": "8.8.8.8"}
    response = client.post("/v1/lookup", json=payload, headers=VALID_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["ip"] == "8.8.8.8"
    assert "geo" in data
    assert "asn" in data
    assert "threats" in data

def test_configure_splunk(client):
    """Test Splunk configuration"""
    payload = {
        "hec_url": "https://splunk.example.com:8088/services/collector",
        "token": "test-token"
    }
    response = client.post("/v1/outputs/splunk", json=payload, headers=VALID_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "configured"

def test_configure_elastic(client):
    """Test Elasticsearch configuration"""
    payload = {
        "url": "https://elastic.example.com:9200",
        "username": "elastic",
        "password": "test-pass"
    }
    response = client.post("/v1/outputs/elastic", json=payload, headers=VALID_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "configured"

def test_metrics_endpoint(client):
    """Test metrics endpoint"""
    response = client.get("/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "requests_total" in data
    assert "requests_failed" in data
    assert "records_processed" in data

# Error cases
def test_ingest_no_auth(client):
    """Test ingest without authentication"""
    payload = {"collector_id": "test", "format": "zeek.conn", "records": []}
    response = client.post("/v1/ingest", json=payload)
    assert response.status_code == 401

def test_ingest_invalid_format(client):
    """Test ingest with invalid format"""
    payload = {"collector_id": "test", "format": "invalid", "records": []}
    response = client.post("/v1/ingest", json=payload, headers=VALID_HEADERS)
    assert response.status_code == 422

def test_ingest_too_many_records(client):
    """Test ingest with too many records"""
    records = [{"ts": 1723351200, "id_orig_h": "1.1.1.1", "id_orig_p": 80, 
                "id_resp_h": "2.2.2.2", "id_resp_p": 443, "proto": "tcp"} for _ in range(10001)]
    payload = {"collector_id": "test", "format": "zeek.conn", "records": records}
    response = client.post("/v1/ingest", json=payload, headers=VALID_HEADERS)
    assert response.status_code == 413

def test_lookup_invalid_ip(client):
    """Test lookup with invalid IP"""
    payload = {"ip": "invalid-ip"}
    response = client.post("/v1/lookup", json=payload, headers=VALID_HEADERS)
    assert response.status_code == 400

def test_lookup_missing_ip(client):
    """Test lookup without IP"""
    payload = {}
    response = client.post("/v1/lookup", json=payload, headers=VALID_HEADERS)
    assert response.status_code == 400

if __name__ == "__main__":
    pytest.main([__file__])
