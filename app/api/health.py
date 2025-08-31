"""
Health check endpoint - no authentication required
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}

@router.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}
