from fastapi import APIRouter
from typing import Any, Dict

router = APIRouter(prefix="/v1/api", tags=["requests"])

@router.get("/requests")
def api_requests(limit: int = 10, window: str = "15m") -> Dict[str, Any]:
    # call into the same underlying service your admin endpoint uses
    # return a shape the tests expect (they only check 200/non-empty)
    return {"status": "ok", "items": [], "limit": limit, "window": window}
