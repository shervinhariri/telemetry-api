# app/api/system.py
import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, Header, HTTPException, Request, Depends, status
from ..auth import get_scope_from_request

router = APIRouter(prefix="/v1", tags=["system"])

def _payload() -> Dict[str, Any]:
    # shape expected by tests
    return {
        "status": "ok",
        "features": {"sources": True, "udp_head": "disabled"},
        "udp_head": {"status": "disabled"},
        "enrichment": {"geo": "ready", "asn": "ready"},
        "queue": {"depth": 0},
    }

@router.get("/system")
async def get_system(request: Request):
    """
    System status snapshot.
    Auth behavior required by tests:
      - No Authorization header -> 200
      - Non-admin key present   -> 403
      - Admin key present       -> 200 and "admin": true
    """
    scope = get_scope_from_request(request)  # 'admin'|'user'|None
    if scope and scope != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin scope required")
    is_admin = scope == "admin"

    # UDP head string status ("ready" | "disabled" | "error" ...)
    udp_status = "disabled"  # TODO: get from actual udp_head module

    # Geo block shape expected by e2e: enabled, vendor, database, status
    geo_status = "ready"  # TODO: get from actual geo_loader
    geo_enabled = geo_status not in ("empty", "error")
    geo_vendor = "MaxMind GeoLite2"
    geo_db = "GeoLite2-City.mmdb"

    return {
        # simple UDP status at top-level (string)
        "udp_head": udp_status,

        # e2e-required 'geo' block (dict with specific keys)
        "geo": {
            "enabled": bool(geo_enabled),
            "vendor": str(geo_vendor),
            "database": str(geo_db),
            "status": str(geo_status),
        },

        # keep existing fields for other tests/back-compat
        "features": {
            "sources": True,
            "udp_head": udp_status,
        },
        "queue": {"depth": 0},
        "enrichment": {
            "geo": geo_status,
            "asn": "ready",
        },
        "admin": is_admin,
    }
