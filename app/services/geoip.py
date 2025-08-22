import os
from functools import lru_cache
import geoip2.database

MMDB_PATH = os.getenv("GEOIP_MMDB_PATH", "")

@lru_cache(maxsize=1)
def _reader():
    if not MMDB_PATH or not os.path.exists(MMDB_PATH):
        return None
    return geoip2.database.Reader(MMDB_PATH)

def lookup_ip(ip: str):
    r = _reader()
    if not r: return None
    try:
        rec = r.city(ip)
        return {
            "country": rec.country.iso_code,
            "city": rec.city.name,
            "lat": rec.location.latitude,
            "lon": rec.location.longitude
        }
    except Exception:
        return None

def set_mmdb_path(path: str):
    global MMDB_PATH
    MMDB_PATH = path
    _reader.cache_clear()
