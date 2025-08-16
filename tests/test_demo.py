"""
Tests for demo functionality
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock
from app.demo.generator import DemoService, demo_service
from app.main import DEMO_MODE, DEMO_EPS, DEMO_DURATION_SEC, DEMO_VARIANTS


class TestDemoService:
    """Test the DemoService class."""
    
    def setup_method(self):
        """Reset demo service before each test."""
        demo_service.is_running = False
        demo_service.task = None
        demo_service.start_time = None
    
    def test_demo_service_initialization(self):
        """Test demo service initializes correctly."""
        service = DemoService()
        assert service.is_running == False
        assert service.task is None
        assert service.start_time is None
        assert len(service.internal_ranges) == 3
        assert len(service.external_ips) > 0
        assert len(service.threat_ips) > 0
    
    def test_generate_internal_ip(self):
        """Test internal IP generation."""
        service = DemoService()
        ip = service._generate_internal_ip()
        
        # Should be a valid IP in internal ranges
        assert ip.count('.') == 3
        parts = ip.split('.')
        assert len(parts) == 4
        assert all(0 <= int(part) <= 255 for part in parts)
        
        # Should be in internal ranges
        is_internal = False
        for network in service.internal_ranges:
            if network.startswith(parts[0]):
                is_internal = True
                break
        assert is_internal
    
    def test_generate_external_ip(self):
        """Test external IP generation."""
        service = DemoService()
        ip = service._generate_external_ip()
        
        # Should be a valid IP
        assert ip.count('.') == 3
        parts = ip.split('.')
        assert len(parts) == 4
        assert all(0 <= int(part) <= 255 for part in parts)
        
        # Should be in external or threat IPs
        assert ip in service.external_ips or ip in service.threat_ips
    
    def test_generate_netflow_event(self):
        """Test NetFlow event generation."""
        service = DemoService()
        event = service._generate_netflow_event()
        
        required_fields = ['ts', 'src_ip', 'dst_ip', 'src_port', 'dst_port', 'protocol', 'bytes', 'packets', 'demo']
        for field in required_fields:
            assert field in event
        
        assert event['demo'] == True
        assert isinstance(event['ts'], int)
        assert isinstance(event['src_port'], int)
        assert isinstance(event['dst_port'], int)
        assert event['protocol'] in ['tcp', 'udp']
        assert 64 <= event['bytes'] <= 50000
        assert 1 <= event['packets'] <= 100
    
    def test_generate_zeek_event(self):
        """Test Zeek event generation."""
        service = DemoService()
        event = service._generate_zeek_event()
        
        required_fields = ['ts', 'uid', 'id_orig_h', 'id_orig_p', 'id_resp_h', 'id_resp_p', 'proto', 'demo']
        for field in required_fields:
            assert field in event
        
        assert event['demo'] == True
        assert isinstance(event['ts'], int)
        assert event['uid'].startswith('C')
        assert event['proto'] in ['tcp', 'udp']
    
    def test_get_status(self):
        """Test status reporting."""
        service = DemoService()
        status = service.get_status()
        
        expected_fields = ['running', 'demo_mode', 'eps', 'duration_sec', 'variants', 'elapsed_sec', 'remaining_sec', 'start_time']
        for field in expected_fields:
            assert field in status
        
        assert status['running'] == False
        assert status['demo_mode'] == DEMO_MODE
        assert status['eps'] == DEMO_EPS
        assert status['duration_sec'] == DEMO_DURATION_SEC
        assert status['variants'] == DEMO_VARIANTS
        assert status['elapsed_sec'] == 0
        assert status['remaining_sec'] == DEMO_DURATION_SEC
    
    @pytest.mark.asyncio
    async def test_start_demo_service(self):
        """Test starting demo service."""
        with patch('app.demo.generator.DEMO_MODE', True):
            service = DemoService()
            success = await service.start()
            
            assert success == True
            assert service.is_running == True
            assert service.task is not None
            assert service.start_time is not None
            
            # Clean up
            await service.stop()
    
    @pytest.mark.asyncio
    async def test_start_demo_service_disabled(self):
        """Test starting demo service when disabled."""
        with patch('app.demo.generator.DEMO_MODE', False):
            service = DemoService()
            success = await service.start()
            
            assert success == False
            assert service.is_running == False
    
    @pytest.mark.asyncio
    async def test_stop_demo_service(self):
        """Test stopping demo service."""
        with patch('app.demo.generator.DEMO_MODE', True):
            service = DemoService()
            
            # Start first
            await service.start()
            assert service.is_running == True
            
            # Then stop
            success = await service.stop()
            assert success == True
            assert service.is_running == False
    
    @pytest.mark.asyncio
    async def test_stop_demo_service_not_running(self):
        """Test stopping demo service when not running."""
        service = DemoService()
        success = await service.stop()
        
        assert success == False
        assert service.is_running == False


class TestDemoConfiguration:
    """Test demo configuration."""
    
    def test_demo_configuration_defaults(self):
        """Test demo configuration defaults."""
        assert isinstance(DEMO_MODE, bool)
        assert isinstance(DEMO_EPS, int)
        assert isinstance(DEMO_DURATION_SEC, int)
        assert isinstance(DEMO_VARIANTS, list)
        
        assert DEMO_EPS > 0
        assert DEMO_DURATION_SEC > 0
        assert len(DEMO_VARIANTS) > 0
        assert all(variant in ['netflow', 'zeek'] for variant in DEMO_VARIANTS)
