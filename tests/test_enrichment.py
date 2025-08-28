"""
Tests for enrichment modules
"""

import pytest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock
from app.enrich.geo import GeoIPLoader, ASNLoader, enrich_geo_asn
from app.enrich.ti import ThreatIntelLoader, match_ip, match_domain
from app.enrich.risk import score

class TestGeoIPLoader:
    """Test GeoIP loader"""
    
    def test_geoip_loader_init(self):
        """Test GeoIP loader initialization"""
        loader = GeoIPLoader()
        assert loader.name == "geoip"
        assert not loader.loaded
        assert loader.db_path == "/app/data/GeoLite2-City.mmdb"
    
    @patch('builtins.__import__')
    def test_geoip_loader_load_success(self, mock_import):
        """Test successful GeoIP database load"""
        with tempfile.NamedTemporaryFile() as tmp:
            loader = GeoIPLoader()
            loader.db_path = tmp.name
            
            # Mock maxminddb import
            mock_maxminddb = MagicMock()
            mock_reader = MagicMock()
            mock_maxminddb.open_database.return_value = mock_reader
            mock_import.return_value = mock_maxminddb
            
            result = loader.load()
            
            assert result is True
            assert loader.loaded is True
            assert loader.last_refresh > 0
            mock_maxminddb.open_database.assert_called_once_with(tmp.name)
    
    def test_geoip_loader_load_missing_file(self):
        """Test GeoIP loader with missing database file"""
        loader = GeoIPLoader()
        loader.db_path = "/nonexistent/file.mmdb"
        
        result = loader.load()
        
        assert result is False
        assert not loader.loaded
    
    @patch('builtins.__import__')
    def test_geoip_lookup(self, mock_import):
        """Test GeoIP lookup"""
        loader = GeoIPLoader()
        mock_maxminddb = MagicMock()
        mock_reader = MagicMock()
        mock_reader.get.return_value = {
            "country": {"iso_code": "US"},
            "city": {"names": {"en": "New York"}},
            "location": {"latitude": 40.7128, "longitude": -74.0060, "time_zone": "America/New_York"}
        }
        mock_maxminddb.open_database.return_value = mock_reader
        mock_import.return_value = mock_maxminddb
        loader._reader = mock_reader
        loader.loaded = True
        
        result = loader.lookup("8.8.8.8")
        
        assert result is not None
        assert result["country"] == "US"
        assert result["city"] == "New York"
        assert result["latitude"] == 40.7128
        assert result["longitude"] == -74.0060
        assert result["timezone"] == "America/New_York"

class TestASNLoader:
    """Test ASN loader"""
    
    def test_asn_loader_init(self):
        """Test ASN loader initialization"""
        loader = ASNLoader()
        assert loader.name == "asn"
        assert not loader.loaded
        assert loader.db_path == "/app/data/asn.csv"
    
    def test_asn_loader_load_csv(self):
        """Test ASN loader with CSV file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
            # Write test CSV data
            tmp.write("ip_range,asn,organization\n")
            tmp.write("8.8.8.0/24,15169,Google LLC\n")
            tmp.write("1.1.1.0/24,13335,Cloudflare\n")
            tmp.close()
            
            try:
                loader = ASNLoader()
                loader.db_path = tmp.name
                
                result = loader.load()
                
                assert result is True
                assert loader.loaded is True
                assert len(loader._asn_data) == 2
                assert "8.8.8.0/24" in loader._asn_data
                assert loader._asn_data["8.8.8.0/24"]["asn"] == "15169"
                assert loader._asn_data["8.8.8.0/24"]["organization"] == "Google LLC"
            finally:
                os.unlink(tmp.name)
    
    def test_asn_lookup(self):
        """Test ASN lookup"""
        loader = ASNLoader()
        loader._asn_data = {
            "8.8.8": {"asn": "15169", "organization": "Google LLC"}  # Simplified range
        }
        loader.loaded = True
        
        result = loader.lookup("8.8.8.8")
        
        assert result is not None
        assert result["asn"] == "15169"
        assert result["organization"] == "Google LLC"

class TestThreatIntelLoader:
    """Test Threat Intelligence loader"""
    
    def test_ti_loader_init(self):
        """Test Threat Intelligence loader initialization"""
        loader = ThreatIntelLoader()
        assert loader.name == "threatintel"
        assert not loader.loaded
        assert loader.data_dir == "/app/data/ti"
    
    def test_ti_loader_load_ip_list(self):
        """Test loading IP threat list"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            ip_dir = os.path.join(tmp_dir, "ips")
            os.makedirs(ip_dir)
            
            # Create test IP list
            ip_file = os.path.join(ip_dir, "malicious_ips.txt")
            with open(ip_file, 'w') as f:
                f.write("192.168.1.100\n")
                f.write("10.0.0.50\n")
                f.write("# This is a comment\n")
                f.write("172.16.0.25\n")
            
            loader = ThreatIntelLoader()
            loader.data_dir = tmp_dir
            
            result = loader.load()
            
            assert result is True
            assert loader.loaded is True
            assert "malicious_ips.txt" in loader.ip_lists
            assert len(loader.ip_lists["malicious_ips.txt"]) == 3
            assert "192.168.1.100" in loader.ip_lists["malicious_ips.txt"]
            assert "10.0.0.50" in loader.ip_lists["malicious_ips.txt"]
            assert "172.16.0.25" in loader.ip_lists["malicious_ips.txt"]
    
    def test_ti_loader_match_ip(self):
        """Test IP matching"""
        loader = ThreatIntelLoader()
        loader.ip_lists = {
            "malicious_ips.txt": {"192.168.1.100", "10.0.0.50"}
        }
        loader.loaded = True
        
        matches = loader.match_ip("192.168.1.100")
        
        assert len(matches) == 1
        assert matches[0]["type"] == "ip"
        assert matches[0]["source"] == "malicious_ips.txt"
        assert matches[0]["value"] == "192.168.1.100"
        assert matches[0]["category"] == "malicious"
    
    def test_ti_loader_match_domain(self):
        """Test domain matching"""
        loader = ThreatIntelLoader()
        loader.domain_lists = {
            "malicious_domains.txt": {"evil.com", "malware.net"}
        }
        loader.loaded = True
        
        matches = loader.match_domain("evil.com")
        
        assert len(matches) == 1
        assert matches[0]["type"] == "domain"
        assert matches[0]["source"] == "malicious_domains.txt"
        assert matches[0]["value"] == "evil.com"
        assert matches[0]["category"] == "malicious"

class TestEnrichmentIntegration:
    """Test enrichment integration"""
    
    def test_enrich_geo_asn(self):
        """Test GeoIP and ASN enrichment integration"""
        with patch('app.enrich.geo.geoip_loader') as mock_geoip, \
             patch('app.enrich.geo.asn_loader') as mock_asn:
            
            mock_geoip.lookup.return_value = {
                "country": "US",
                "city": "New York"
            }
            mock_asn.lookup.return_value = {
                "asn": "15169",
                "organization": "Google LLC"
            }
            
            result = enrich_geo_asn("8.8.8.8")
            
            assert result is not None
            assert "geo" in result
            assert "asn" in result
            assert result["geo"]["country"] == "US"
            assert result["asn"]["asn"] == "15169"
    
    def test_risk_scoring(self):
        """Test risk scoring"""
        record = {
            "src_ip": "192.168.1.100",
            "dst_ip": "8.8.8.8",
            "src_port": 12345,
            "dst_port": 80,
            "proto": "tcp",
            "bytes": 1000,
            "packets": 10
        }
        
        ti_matches = [
            {"type": "ip", "source": "malicious_ips.txt", "value": "192.168.1.100"}
        ]
        
        risk_score = score(record, ti_matches)
        
        assert risk_score >= 50  # Base score from TI match
        assert risk_score <= 100  # Capped at 100
    
    def test_risk_scoring_suspicious_port(self):
        """Test risk scoring with suspicious port"""
        record = {
            "src_ip": "192.168.1.100",
            "dst_ip": "8.8.8.8",
            "src_port": 12345,
            "dst_port": 3389,  # RDP - suspicious
            "proto": "tcp",
            "bytes": 1000,
            "packets": 10
        }
        
        risk_score = score(record, [])
        
        assert risk_score >= 20  # Suspicious port penalty
