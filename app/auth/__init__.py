# app/auth/__init__.py
import json, hashlib, os
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

# NOTE: these relative imports are correct because this file
# is inside the 'app/auth' package.
from ..db import SessionLocal
from ..models.apikey import ApiKey

__all__ = ["get_db", "require_key", "require_admin"]

ENV_FALLBACK_KEY = os.getenv("API_KEY", "TEST_ADMIN_KEY")

def _token_matches_env_admin(token: str) -> bool:
    return bool(token) and token == ENV_FALLBACK_KEY

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _extract_token(req: Request):
    auth = req.headers.get("authorization") or req.headers.get("Authorization")
    if auth:
        parts = auth.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        if len(parts) == 1:
            return parts[0]
    x = req.headers.get("x-api-key") or req.headers.get("X-API-Key")
    return x.strip() if x else None

def require_key(req: Request, db: Session = Depends(get_db)) -> ApiKey:
    token = _extract_token(req)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    
    # Check env fallback first for admin access
    if _token_matches_env_admin(token):
        # Create a mock ApiKey object for env admin
        class MockApiKey:
            def __init__(self):
                self._scopes = ["admin"]
        return MockApiKey()
    
    try:
        h = _sha256(token)
        key = db.query(ApiKey).filter(ApiKey.hash == h, ApiKey.disabled == False).one_or_none()
        if not key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        try:
            scopes = json.loads(key.scopes) if isinstance(key.scopes, str) else (key.scopes or [])
        except Exception:
            scopes = []
        setattr(key, "_scopes", scopes)
        return key
    except OperationalError as e:
        # If schema isn't initialized yet, allow env fallback key
        if "no such table: api_keys" in str(e).lower():
            if _token_matches_env_admin(token):
                # Create a mock ApiKey object for env admin
                class MockApiKey:
                    def __init__(self):
                        self._scopes = ["admin"]
                return MockApiKey()
        # re-raise for other DB issues
        raise

def require_admin(k: ApiKey = Depends(require_key)) -> ApiKey:
    scopes = getattr(k, "_scopes", [])
    if "admin" not in scopes and "*" not in scopes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin scope required")
    return k
