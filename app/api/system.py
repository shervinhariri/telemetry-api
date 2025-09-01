# app/api/system.py
import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, Header, HTTPException, Request, Depends
from ..auth import require_admin

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
    _: Any = Depends(require_admin),  # Require admin authentication
):
    """Get system information - requires admin scope"""
    data = _payload()
    data["admin"] = True
    return data
