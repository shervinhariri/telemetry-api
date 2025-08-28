"""
GeoIP and ASN enrichment module
Uses MaxMind GeoLite2 for GeoIP and ASN data
"""

import os
import time
import logging
from typing import Dict, Any, Optional
from .base import EnrichmentLoader

logger = logging.getLogger("enrich.geo")

class GeoIPLoader(EnrichmentLoader):
    """GeoIP loader using MaxMind GeoLite2"""
    
    def __init__(self):
        super().__init__("geoip")
        self.db_path = os.getenv("GEOIP_DB_PATH", "/app/data/GeoLite2-City.mmdb")
        self.last_refresh = 0
        self.loaded = False
        self._reader = None
        
    def load(self) -> bool:
        """Load GeoIP database"""
        try:
            # Try to import maxminddb
            try:
                import maxminddb
            except ImportError:
                logger.warning("maxminddb not available, GeoIP enrichment disabled")
                return False
            
            # Check if database file exists
            if not os.path.exists(self.db_path):
                logger.warning(f"GeoIP database not found at {self.db_path}")
                return False
            
            # Load the database
            self._reader = maxminddb.open_database(self.db_path)
            self.loaded = True
            self.last_refresh = time.time()
            
            # Update metrics
            from ..services.prometheus_metrics import prometheus_metrics
            prometheus_metrics.set_geoip_loaded(True)
            prometheus_metrics.set_geoip_last_refresh(self.last_refresh)
            
            logger.info("GeoIP database loaded successfully", extra={
                "component": "enrich.geo",
                "event": "loaded",
                "db_path": self.db_path
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load GeoIP database: {e}")
            self.loaded = False
            return False
    
    def lookup(self, ip: str) -> Optional[Dict[str, Any]]:
        """Lookup GeoIP information for an IP address"""
        if not self.loaded or not self._reader:
            return None
            
        try:
            result = self._reader.get(ip)
            if result:
                return {
                    "country": result.get("country", {}).get("iso_code"),
                    "city": result.get("city", {}).get("names", {}).get("en"),
                    "latitude": result.get("location", {}).get("latitude"),
                    "longitude": result.get("location", {}).get("longitude"),
                    "timezone": result.get("location", {}).get("time_zone")
                }
        except Exception as e:
            logger.debug(f"GeoIP lookup failed for {ip}: {e}")
            
        return None

class ASNLoader(EnrichmentLoader):
    """ASN loader using Team Cymru or local CSV"""
    
    def __init__(self):
        super().__init__("asn")
        self.db_path = os.getenv("ASN_DB_PATH", "/app/data/asn.csv")
        self.last_refresh = 0
        self.loaded = False
        self._asn_data = {}
        
    def load(self) -> bool:
        """Load ASN database"""
        try:
            # Try to load from local CSV first
            if os.path.exists(self.db_path):
                return self._load_from_csv()
            
            # Fallback to Team Cymru (placeholder)
            logger.info("ASN database not found locally, using Team Cymru fallback")
            return self._load_from_cymru()
            
        except Exception as e:
            logger.error(f"Failed to load ASN database: {e}")
            self.loaded = False
            return False
    
    def _load_from_csv(self) -> bool:
        """Load ASN data from local CSV file"""
        try:
            import csv
            
            with open(self.db_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Expected columns: ip_range, asn, organization
                    ip_range = row.get('ip_range', '')
                    asn = row.get('asn', '')
                    org = row.get('organization', '')
                    
                    if ip_range and asn:
                        self._asn_data[ip_range] = {
                            "asn": asn,
                            "organization": org
                        }
            
            self.loaded = True
            self.last_refresh = time.time()
            
            # Update metrics
            from ..services.prometheus_metrics import prometheus_metrics
            prometheus_metrics.set_asn_loaded(True)
            prometheus_metrics.set_asn_last_refresh(self.last_refresh)
            
            logger.info(f"ASN database loaded from CSV: {len(self._asn_data)} entries")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load ASN CSV: {e}")
            return False
    
    def _load_from_cymru(self) -> bool:
        """Load ASN data from Team Cymru (placeholder)"""
        # This is a placeholder - in production, you'd implement Team Cymru API
        logger.info("Team Cymru ASN loading not implemented yet")
        return False
    
    def lookup(self, ip: str) -> Optional[Dict[str, Any]]:
        """Lookup ASN information for an IP address"""
        if not self.loaded:
            return None
            
        # Simple IP range matching (placeholder)
        # In production, you'd implement proper IP range matching
        for ip_range, data in self._asn_data.items():
            if self._ip_in_range(ip, ip_range):
                return data
                
        return None
    
    def _ip_in_range(self, ip: str, ip_range: str) -> bool:
        """Check if IP is in range (placeholder implementation)"""
        # This is a simplified implementation
        # In production, you'd use proper IP range matching
        return ip.startswith(ip_range.split('/')[0])

# Global loader instances
geoip_loader = GeoIPLoader()
asn_loader = ASNLoader()

def enrich_geo_asn(ip: str) -> Optional[Dict[str, Any]]:
    """Enrich IP with GeoIP and ASN data"""
    result = {}
    
    # GeoIP lookup
    geo_data = geoip_loader.lookup(ip)
    if geo_data:
        result["geo"] = geo_data
    
    # ASN lookup
    asn_data = asn_loader.lookup(ip)
    if asn_data:
        result["asn"] = asn_data
    
    return result if result else None

def initialize_enrichment():
    """Initialize enrichment loaders"""
    geoip_loader.load()
    asn_loader.load()
