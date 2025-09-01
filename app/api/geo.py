from fastapi import APIRouter
from typing import Dict, Any, List

router = APIRouter(prefix="/v1", tags=["geo"])

# Note: /geo/download endpoint is implemented in jobs.py with proper admin protection
# This router is kept for future geo-related endpoints
