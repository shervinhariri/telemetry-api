# app/api/utils.py
from fastapi import APIRouter, Request, Depends, HTTPException
from app.security import get_client_ip
from app.auth.deps import require_scopes  # allow any authenticated key
from app.config import get_trust_proxy

router = APIRouter()

@router.get("/v1/utils/client-ip")
def get_ui_client_ip(request: Request, _=Depends(require_scopes("admin", "read_metrics", "ingest"))):
    ip = get_client_ip(request, trust_proxy=get_trust_proxy())
    if not ip:
        raise HTTPException(status_code=400, detail="cannot_determine_ip")
    return {"client_ip": ip}
