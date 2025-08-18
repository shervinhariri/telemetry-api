from fastapi import Request, HTTPException, status
from app.db import SessionLocal
from app.models.apikey import ApiKey
from app.models.tenant import Tenant
import hashlib

def _hash(s: str) -> str: 
    return hashlib.sha256(s.encode()).hexdigest()

async def authenticate(request: Request):
    auth = request.headers.get("authorization","")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = auth.split(" ",1)[1].strip()
    
    with SessionLocal() as db:
        key = db.query(ApiKey).filter(ApiKey.hash == _hash(token), ApiKey.disabled == False).first()
        if not key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        tenant_id = key.tenant_id

        # Optional admin override
        override = request.headers.get("X-Tenant-ID")
        if override:
            if "admin" not in (key.scopes or []):
                raise HTTPException(status_code=403, detail="X-Tenant-ID override requires admin scope")
            # ensure target tenant exists
            if not db.get(Tenant, override):
                raise HTTPException(status_code=404, detail="Tenant not found")
            tenant_id = override

        # Attach to request
        request.state.scopes = key.scopes or []
        request.state.tenant_id = tenant_id
        request.state.key_id = key.key_id
