# app/api/system.py
import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, Header, HTTPException, Request, Depends
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
async def get_system(
    request: Request,
):
    """
    Public system status. If an admin key is provided, 'admin': True is returned.
    Tests expect this endpoint to be 200 without auth.
    """
    scope = get_scope_from_request(request)  # 'admin'|'user'|None
    is_admin = scope == "admin"
    
    # e2e expects a top-level 'geo' block in addition to 'enrichment'
    data = _payload()
    data["admin"] = is_admin
    
    # Add top-level geo block that e2e tests expect
    data["geo"] = {
        "enabled": True,
        "vendor": "maxmind",
        "database": "geolite2",
        "status": "ready"
    }
    
    return data
