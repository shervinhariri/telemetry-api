from typing import Optional, Dict, Any
try:
    import geoip2.database
except ImportError:
    geoip2 = None

class ASNEnricher:
    def __init__(self, asn_db_path: str):
        self.asn_db_path = asn_db_path
        self.reader = None
        if geoip2:
            try:
                self.reader = geoip2.database.Reader(self.asn_db_path)
            except Exception:
                self.reader = None

    def lookup(self, ip: str) -> Optional[Dict[str, Any]]:
        if not self.reader:
            return None
        try:
            r = self.reader.asn(ip)
            return {"asn": r.autonomous_system_number, "org": r.autonomous_system_organization}
        except Exception:
            return None
