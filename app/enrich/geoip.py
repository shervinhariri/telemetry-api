from typing import Optional, Dict, Any
try:
    import geoip2.database
except ImportError:
    geoip2 = None

class GeoIPEnricher:
    def __init__(self, city_db_path: str):
        self.city_db_path = city_db_path
        self.reader = None
        if geoip2:
            try:
                self.reader = geoip2.database.Reader(self.city_db_path)
            except Exception:
                self.reader = None

    def lookup(self, ip: str) -> Optional[Dict[str, Any]]:
        if not self.reader:
            return None
        try:
            r = self.reader.city(ip)
            return {
                "country": r.country.iso_code,
                "city": r.city.name,
                "location": {"lat": r.location.latitude, "lon": r.location.longitude}
            }
        except Exception:
            return None
