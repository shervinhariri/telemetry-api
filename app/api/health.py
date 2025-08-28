"""
Health check endpoint - no authentication required
"""

from fastapi import APIRouter
from ..api.version import get_version_from_file

router = APIRouter()

@router.get("/health", status_code=200)
async def health_check():
    """Health check endpoint - no authentication required"""
    return {
        "status": "ok"
    }
