"""
Health check endpoint - no authentication required
"""

from fastapi import APIRouter, Depends
from ..auth import require_key

router = APIRouter()

@router.get("/health", include_in_schema=False, dependencies=[Depends(require_key)])
async def health():
    return {"status": "ok"}

# Optional unauthenticated probe for kube/docker HEALTHCHECKs:
@router.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}
