from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.services.geoip import set_mmdb_path, lookup_ip

router = APIRouter(tags=["config"])

class GeoIPCfg(BaseModel):
    enabled: bool = True
    path: str

GEOIP_ENABLED = False

@router.put("/config/geoip")
def set_geoip(cfg: GeoIPCfg):
    global GEOIP_ENABLED
    if not cfg.path:
        raise HTTPException(400, "path required")
    set_mmdb_path(cfg.path)
    GEOIP_ENABLED = cfg.enabled
    return {"ok": True, "enabled": GEOIP_ENABLED, "path": cfg.path}

@router.post("/config/geoip/test")
def test_geoip(ip: str = Query(...)):
    hit = lookup_ip(ip)
    return {"enabled": GEOIP_ENABLED, "ip": ip, "geo": hit}
