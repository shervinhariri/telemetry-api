"""
Tests for the system endpoint
"""

import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:80")

def test_system_endpoint_basic(client):
    """Test basic system endpoint response"""
    if hasattr(client, 'app'):
        # TestClient
        response = client.get("/v1/system")
    else:
        # requests.Session
        response = client.get(f"{BASE_URL}/v1/system")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "features" in data
    assert "queue" in data
    assert "geoip" in data
    assert "asn" in data
    assert "threatintel" in data

def test_system_endpoint_udp_head_disabled(client):
    """Test system endpoint with UDP head disabled"""
    with patch('app.config.FEATURES', {'sources': True, 'udp_head': False}), \
         patch('app.udp_head.get_udp_head_status', return_value='disabled'):
        if hasattr(client, 'app'):
            response = client.get("/v1/system")
        else:
            response = client.get(f"{BASE_URL}/v1/system")
        assert response.status_code == 200
        
        data = response.json()
        assert data["features"]["udp_head"] == "disabled"

def test_system_endpoint_udp_head_enabled(client):
    """Test system endpoint with UDP head enabled"""
    with patch('app.config.FEATURES', {'sources': True, 'udp_head': True}), \
         patch('app.udp_head.get_udp_head_status', return_value='ready'):
        if hasattr(client, 'app'):
            response = client.get("/v1/system")
        else:
            response = client.get(f"{BASE_URL}/v1/system")
        assert response.status_code == 200
        
        data = response.json()
        assert data["features"]["udp_head"] == "ready"

def test_system_endpoint_queue_info(client):
    """Test system endpoint includes queue information"""
    if hasattr(client, 'app'):
        response = client.get("/v1/system")
    else:
        response = client.get(f"{BASE_URL}/v1/system")
    assert response.status_code == 200
    
    data = response.json()
    queue_info = data["queue"]
    assert "max_depth" in queue_info
    assert "current_depth" in queue_info
    assert isinstance(queue_info["max_depth"], int)
    assert isinstance(queue_info["current_depth"], int)
    assert queue_info["current_depth"] >= 0
    assert queue_info["max_depth"] > 0

def test_system_endpoint_enrichment_status(client):
    """Test system endpoint includes enrichment status"""
    if hasattr(client, 'app'):
        response = client.get("/v1/system")
    else:
        response = client.get(f"{BASE_URL}/v1/system")
    assert response.status_code == 200
    
    data = response.json()
    
    # Check GeoIP status
    geoip_status = data["geoip"]
    assert "status" in geoip_status
    assert geoip_status["status"] in ["loaded", "missing"]
    
    # Check ASN status
    asn_status = data["asn"]
    assert "status" in asn_status
    assert asn_status["status"] in ["loaded", "missing"]
    
    # Check Threat Intelligence status
    ti_status = data["threatintel"]
    assert "status" in ti_status
    assert ti_status["status"] in ["loaded", "missing"]
    assert "sources" in ti_status
    assert isinstance(ti_status["sources"], list)

def test_system_endpoint_requires_auth(client):
    """Test system endpoint requires authentication"""
    # Create a session without auth headers
    import requests
    s = requests.Session()
    if hasattr(client, 'app'):
        # TestClient without auth
        client.headers = {}
        response = client.get("/v1/system")
    else:
        response = s.get(f"{BASE_URL}/v1/system")
    assert response.status_code == 401

def test_system_endpoint_requires_admin_scope(client):
    """Test system endpoint requires admin scope"""
    # Use a key without admin scope
    import requests
    s = requests.Session()
    s.headers.update({"Authorization": "Bearer TEST_KEY"})
    if hasattr(client, 'app'):
        response = client.get("/v1/system", headers={"Authorization": "Bearer TEST_KEY"})
    else:
        response = s.get(f"{BASE_URL}/v1/system")
    assert response.status_code == 403
