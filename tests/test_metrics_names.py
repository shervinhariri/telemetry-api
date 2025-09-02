import pytest
import requests

BASE_URL = "http://localhost/v1"
HEADERS = {"Authorization": "Bearer TEST_KEY"}

@pytest.mark.metrics
def test_processing_latency_metric_exposed():
    try:
        resp = requests.get(f"{BASE_URL}/metrics/prometheus", headers=HEADERS, timeout=5)
        assert resp.status_code == 200
        body = resp.text
        # Check for the processing latency metric - this will fail until the metric is actually used
        assert "telemetry_processing_latency_ms_bucket" in body, "telemetry_processing_latency_ms_bucket metric not found - ensure it's being observed in the code"
    except (requests.RequestException, ConnectionError):
        pytest.skip("Service not available or requests library not available")

@pytest.mark.metrics
def test_core_metrics_exposed():
    """Test that core telemetry metrics are exposed."""
    try:
        resp = requests.get(f"{BASE_URL}/metrics/prometheus", headers=HEADERS, timeout=5)
        assert resp.status_code == 200
        body = resp.text
        # Check for metrics that should always be present
        assert "telemetry_requests_total" in body
        assert "telemetry_ingest_batch_bytes_bucket" in body
    except (requests.RequestException, ConnectionError):
        pytest.skip("Service not available or requests library not available")
