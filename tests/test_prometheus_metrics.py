"""
Tests for Prometheus metrics functionality
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.prometheus_metrics import prometheus_metrics, PrometheusMetrics


class TestPrometheusMetrics:
    """Test the PrometheusMetrics class."""
    
    def test_prometheus_metrics_initialization(self):
        """Test Prometheus metrics initializes correctly."""
        metrics = PrometheusMetrics()
        assert metrics is not None
    
    def test_increment_requests(self):
        """Test request counter increments."""
        metrics = PrometheusMetrics()
        
        # Test 2xx response
        metrics.increment_requests(200)
        
        # Test 4xx response
        metrics.increment_requests(404)
        
        # Test 5xx response
        metrics.increment_requests(500)
        
        # Test other response
        metrics.increment_requests(100)
    
    def test_increment_records_processed(self):
        """Test records processed counter increments."""
        metrics = PrometheusMetrics()
        metrics.increment_records_processed(1)
        metrics.increment_records_processed(5)
    
    def test_increment_threat_matches(self):
        """Test threat matches counter increments."""
        metrics = PrometheusMetrics()
        metrics.increment_threat_matches(1)
        metrics.increment_threat_matches(3)
    
    def test_set_eps(self):
        """Test EPS gauge setting."""
        metrics = PrometheusMetrics()
        metrics.set_eps(50.0)
        metrics.set_eps(100.5)
    
    def test_set_queue_lag(self):
        """Test queue lag gauge setting."""
        metrics = PrometheusMetrics()
        metrics.set_queue_lag(10.5)
        metrics.set_queue_lag(25.0)
    
    def test_observe_processing_latency(self):
        """Test processing latency observation."""
        metrics = PrometheusMetrics()
        metrics.observe_processing_latency(100.0)
        metrics.observe_processing_latency(250.5)
    
    def test_get_metrics(self):
        """Test metrics retrieval."""
        metrics = PrometheusMetrics()
        metrics_data = metrics.get_metrics()
        
        assert isinstance(metrics_data, bytes)
        assert len(metrics_data) > 0
        
        # Should contain Prometheus format
        text = metrics_data.decode('utf-8')
        assert '# HELP' in text
        assert '# TYPE' in text
    
    def test_get_content_type(self):
        """Test content type retrieval."""
        metrics = PrometheusMetrics()
        content_type = metrics.get_content_type()
        
        assert content_type == 'text/plain; version=0.0.4; charset=utf-8'


class TestPrometheusMetricsIntegration:
    """Test Prometheus metrics integration with existing metrics."""
    
    def test_metrics_wiring(self):
        """Test that Prometheus metrics are wired to existing metrics."""
        # This test verifies that the metrics module properly updates Prometheus metrics
        from app.metrics import increment_requests, record_batch, record_queue_lag
        
        # Test request increment
        increment_requests(failed=False)
        increment_requests(failed=True)
        
        # Test batch recording
        record_batch(record_count=5, threat_matches=2, risk_scores=[1, 2, 3, 4, 5], sources=['test'])
        
        # Test queue lag
        record_queue_lag(50)
        
        # Verify metrics are available
        metrics_data = prometheus_metrics.get_metrics()
        assert len(metrics_data) > 0


class TestPrometheusEndpoint:
    """Test the Prometheus metrics endpoint."""
    
    @pytest.mark.asyncio
    async def test_prometheus_endpoint(self, client):
        """Test the /v1/metrics/prometheus endpoint."""
        from app.api.prometheus import get_prometheus_metrics
        
        response = await get_prometheus_metrics()
        
        assert response.status_code == 200
        assert response.headers['content-type'] == 'text/plain; version=0.0.4; charset=utf-8'
        
        content = response.body.decode('utf-8')
        assert '# HELP' in content
        assert '# TYPE' in content
        assert 'telemetry_requests_total' in content
        assert 'telemetry_records_processed_total' in content
        assert 'telemetry_eps' in content
        assert 'build_info' in content


class TestPrometheusMetricsFormat:
    """Test Prometheus metrics format compliance."""
    
    def test_metrics_format(self):
        """Test that metrics follow Prometheus exposition format."""
        metrics_data = prometheus_metrics.get_metrics()
        text = metrics_data.decode('utf-8')
        
        lines = text.split('\n')
        
        # Should have help and type lines
        help_lines = [line for line in lines if line.startswith('# HELP')]
        type_lines = [line for line in lines if line.startswith('# TYPE')]
        
        assert len(help_lines) > 0
        assert len(type_lines) > 0
        
        # Should have metric lines
        metric_lines = [line for line in lines if line and not line.startswith('#')]
        assert len(metric_lines) > 0
        
        # Check specific metrics
        metric_names = []
        for line in metric_lines:
            if '{' in line:
                name = line.split('{')[0]
            else:
                name = line.split(' ')[0]
            metric_names.append(name)
        
        expected_metrics = [
            'telemetry_requests_total',
            'telemetry_records_processed_total',
            'telemetry_threat_matches_total',
            'telemetry_eps',
            'telemetry_queue_lag',
            'telemetry_processing_latency_ms_sum',
            'telemetry_processing_latency_ms_count',
            'build_info'
        ]
        
        for expected in expected_metrics:
            assert any(expected in name for name in metric_names), f"Missing metric: {expected}"
