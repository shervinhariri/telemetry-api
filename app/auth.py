# app/auth.py
import json, hashlib, os
from typing import Optional, List
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models.apikey import ApiKey

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _extract_token(req: Request) -> Optional[str]:
    # Authorization: Bearer <token>   OR   Authorization: <token>
    auth = req.headers.get("authorization") or req.headers.get("Authorization")
    if auth:
        parts = auth.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        if len(parts) == 1:
            return parts[0]
    # X-API-Key: <token>
    x = req.headers.get("x-api-key") or req.headers.get("X-API-Key")
    if x:
        return x.strip()
    return None

def _norm_scopes(scopes) -> List[str]:
    if scopes is None:
        return []
    if isinstance(scopes, list):
        return scopes
    if isinstance(scopes, str):
        try:
            val = json.loads(scopes)
            return val if isinstance(val, list) else []
        except Exception:
            return []
    return []

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def require_key(req: Request, db: Session = Depends(get_db)) -> ApiKey:
    token = _extract_token(req)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    h = _sha256(token)
    key = db.query(ApiKey).filter(ApiKey.hash == h, ApiKey.disabled == False).one_or_none()
    if not key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    key._norm_scopes = _norm_scopes(key.scopes)
    return key

def require_admin(key: ApiKey = Depends(require_key)) -> ApiKey:
    scopes = getattr(key, "_norm_scopes", _norm_scopes(key.scopes))
    if "admin" not in scopes and "*" not in scopes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin scope required")
    return key
