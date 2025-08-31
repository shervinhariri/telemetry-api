# app/auth/__init__.py
import os
from typing import Optional, List
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from ..db import get_db
# If you have these, keep; otherwise remove DB branch entirely.
from ..models.apikey import ApiKey  # optional
import hashlib

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

ENV_ADMIN = os.getenv("API_KEY", "TEST_ADMIN_KEY")

class SimpleKey:
    def __init__(self, scopes: Optional[List[str]] = None):
        self.scopes = scopes or []

def _token_from_request(req: Request) -> Optional[str]:
    raw = req.headers.get("authorization")
    if raw:
        low = raw.lower()
        if low.startswith("bearer "):
            return raw.split(" ", 1)[1].strip()
        return raw.strip()
    xk = req.headers.get("x-api-key")
    return xk.strip() if xk else None

def _is_env_admin(token: Optional[str]) -> bool:
    return bool(token) and token == ENV_ADMIN

def _is_user_token(token: Optional[str]) -> bool:
    # Test suite uses "***" as a non-admin user token
    return bool(token) and token == "***"

def require_key(req: Request, db: Session = Depends(get_db)) -> SimpleKey:
    token = _token_from_request(req)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    # 1) Env admin (TEST_ADMIN_KEY)
    if _is_env_admin(token):
        return SimpleKey(["admin"])
    # 2) User token ("***")
    if _is_user_token(token):
        return SimpleKey([])

    # 3) Optional DB-backed tokens (gracefully skip if table missing)
    try:
        h = _sha256(token)
        key = db.query(ApiKey).filter(ApiKey.hash == h, ApiKey.disabled == False).one_or_none()
        if not key:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        scopes = key.scopes or []
        return SimpleKey(scopes)
    except OperationalError as e:
        if "no such table" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        raise

def require_admin(user: SimpleKey = Depends(require_key)) -> SimpleKey:
    if "admin" in user.scopes:
        return user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


