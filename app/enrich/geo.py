import os
from typing import Optional, Dict, Any
try:
    import geoip2.database
except ImportError:
    geoip2 = None

class GeoASNEnricher:
    def __init__(self):
        self.city_db_path = os.getenv("GEOIP_CITY_DB", "/data/geo/GeoLite2-City.mmdb")
        self.asn_db_path = os.getenv("GEOIP_ASN_DB", "/data/geo/GeoLite2-ASN.mmdb")
        self.enable_geoip = os.getenv("ENRICH_ENABLE_GEOIP", "true").lower() == "true"
        self.enable_asn = os.getenv("ENRICH_ENABLE_ASN", "true").lower() == "true"
        
        self.city_reader = None
        self.asn_reader = None
        
        if geoip2 and self.enable_geoip:
            try:
                self.city_reader = geoip2.database.Reader(self.city_db_path)
            except Exception as e:
                print(f"Warning: Could not load GeoIP City DB: {e}")
                
        if geoip2 and self.enable_asn:
            try:
                self.asn_reader = geoip2.database.Reader(self.asn_db_path)
            except Exception as e:
                print(f"Warning: Could not load GeoIP ASN DB: {e}")

    def enrich_geo_asn(self, ip: str) -> Optional[Dict[str, Any]]:
        """Enrich IP with GeoIP and ASN data"""
        if not ip:
            return None
            
        result = {"geo": None, "asn": None}
        
        # GeoIP lookup
        if self.city_reader:
            try:
                r = self.city_reader.city(ip)
                result["geo"] = {
                    "country": r.country.iso_code,
                    "city": r.city.name,
                    "lat": r.location.latitude,
                    "lon": r.location.longitude
                }
            except Exception:
                pass
                
        # ASN lookup
        if self.asn_reader:
            try:
                r = self.asn_reader.asn(ip)
                result["asn"] = {
                    "asn": r.autonomous_system_number,
                    "org": r.autonomous_system_organization
                }
            except Exception:
                pass
                
        return result if result["geo"] or result["asn"] else None

# Global instance
geo_asn_enricher = GeoASNEnricher()

def enrich_geo_asn(ip: str) -> Optional[Dict[str, Any]]:
    """Convenience function to enrich IP with GeoIP and ASN data"""
    return geo_asn_enricher.enrich_geo_asn(ip)
