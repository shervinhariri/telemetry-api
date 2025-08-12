from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import os
import ipaddress
from .enrich.geoip import GeoIPEnricher
from .enrich.asn import ASNEnricher
from .enrich.threat import ThreatMatcher
from .enrich.score import RiskScorer

API_PREFIX = "/v1"

API_KEY = os.getenv("API_KEY", "TEST_KEY")
GEOIP_DB_CITY = os.getenv("GEOIP_DB_CITY", "/data/GeoLite2-City.mmdb")
GEOIP_DB_ASN = os.getenv("GEOIP_DB_ASN", "/data/GeoLite2-ASN.mmdb")
THREATLIST_CSV = os.getenv("THREATLIST_CSV", "/data/threats.csv")

app = FastAPI(title="Live Network Threat Telemetry API (MVP)")

# Enrichers are loaded once on startup
geo = GeoIPEnricher(GEOIP_DB_CITY)
asn = ASNEnricher(GEOIP_DB_ASN)
threats = ThreatMatcher(THREATLIST_CSV)
scorer = RiskScorer()

def require_api_key(auth_header: Optional[str]):
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth_header.split(" ", 1)[1].strip()
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get(f"{API_PREFIX}/health")
async def health():
    return {"status": "ok"}

@app.post(f"{API_PREFIX}/ingest")
async def ingest(request: Request, Authorization: Optional[str] = Header(None)):
    require_api_key(Authorization)
    payload = await request.json()
    # Expect: { "collector_id": "...", "format": "zeek.conn.v1", "records": [ {...}, ... ] }
    fmt = payload.get("format")
    if fmt != "zeek.conn.v1":
        raise HTTPException(status_code=400, detail="Unsupported format (expected zeek.conn.v1 for Stage 3)")
    records = payload.get("records", [])
    enr_records = []
    for rec in records:
        enr = rec.copy()
        src_ip = rec.get("id_orig_h")
        dst_ip = rec.get("id_resp_h")
        # Geo & ASN
        if src_ip:
            enr["src_geo"] = geo.lookup(src_ip)
            enr["src_asn"] = asn.lookup(src_ip)
        if dst_ip:
            enr["dst_geo"] = geo.lookup(dst_ip)
            enr["dst_asn"] = asn.lookup(dst_ip)
        # Threat matches
        matches = threats.match_any([ip for ip in [src_ip, dst_ip] if ip])
        enr["threat"] = {"matches": matches, "matched": len(matches) > 0}
        # Risk scoring
        score, reasons = scorer.score(enr)
        enr["risk_score"] = score
        enr["reasons"] = reasons
        enr_records.append(enr)
    out = {
        "collector_id": payload.get("collector_id"),
        "format": fmt,
        "count": len(enr_records),
        "records": enr_records
    }
    return JSONResponse(out)
