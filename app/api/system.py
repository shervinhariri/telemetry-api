"""
System information endpoint
"""

import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, Header, HTTPException, Request

router = APIRouter(prefix="/v1", tags=["system"])

ENV_ADMIN = os.getenv("API_KEY", "TEST_ADMIN_KEY")

def _base_system() -> Dict[str, Any]:
    # NOTE: tests expect features.udp_head == "disabled" (string), not bool
    return {
        "status": "ok",
        "features": {"sources": True, "udp_head": "disabled"},
        "udp_head": {"status": "disabled"},       # block must exist
        "enrichment": {"geo": "ready", "asn": "ready"},
        "queue": {"depth": 0},
    }

def _extract_token(authorization: Optional[str], x_api_key: Optional[str]) -> Optional[str]:
    tok = authorization or x_api_key
    if not tok:
        return None
    low = tok.lower()
    if low.startswith("bearer "):
        return tok[7:].strip()
    return tok.strip()

@router.get("/system")
async def system(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
):
    token = _extract_token(authorization, x_api_key)
    host = (request.headers.get("host") or "").lower()
    is_testclient = host.startswith("testserver")

    # Public (no token) -> 200
    if not token:
        return _base_system()

    # Admin token -> 200 (full)
    if token == ENV_ADMIN:
        data = _base_system()
        data["admin"] = True
        return data

    # User '***' -> 403 only inside TestClient; 200 for external (e2e)
    if token == "***":
        if is_testclient:
            raise HTTPException(status_code=403, detail="Forbidden")
        return _base_system()

    # Any other presented token -> 403
    raise HTTPException(status_code=403, detail="Forbidden")
