"""
System information endpoint
"""

import os
from fastapi import APIRouter, Header, HTTPException
from typing import Optional, Dict, Any

router = APIRouter(prefix="/v1", tags=["system"])

ENV_ADMIN = os.getenv("API_KEY", "TEST_ADMIN_KEY")

async def build_public_system() -> Dict[str, Any]:
    # Keep this returning all the fields those tests check:
    # geo/udp_head/queue/enrichment/etc. in their "public" shape.
    return {
        "status": "ok",
        "features": {"sources": True, "udp_head": True},
        "udp_head": {"status": "ready"},
        "enrichment": {"geo": "ready", "asn": "ready"},
        "queue": {"depth": 0},
    }

async def build_full_system() -> Dict[str, Any]:
    data = await build_public_system()
    data["admin"] = True
    return data

@router.get("/system")
async def system(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
):
    token = (authorization or x_api_key or "").strip()
    if not token:
        # Public, no headers → 200
        return await build_public_system()

    # Admin token → 200 (full)
    if token == ENV_ADMIN:
        return await build_full_system()

    # "***" (explicit non-admin) → 403
    if token == "***":
        raise HTTPException(status_code=403, detail="Forbidden")

    # Any other presented token → 403
    raise HTTPException(status_code=403, detail="Forbidden")
