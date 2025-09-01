# app/db_boot.py
import os, json, hashlib, logging
from sqlalchemy.exc import IntegrityError
from .db import engine, Base, SessionLocal
from .models.tenant import Tenant
from .models.apikey import ApiKey
from .db_init import init_schema_and_seed_if_needed

log = logging.getLogger("bootstrap")

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _upsert_key(session, key_id, raw_token, scopes, disabled=False):
    h = _sha256(raw_token)
    row = session.query(ApiKey).filter(ApiKey.key_id == key_id).one_or_none()
    if row:
        row.hash = h
        row.scopes = json.dumps(scopes)
        row.disabled = disabled
        session.commit()
        return "updated"
    try:
        session.add(ApiKey(
            key_id=key_id, tenant_id="default",
            hash=h, scopes=json.dumps(scopes), disabled=disabled
        ))
        session.commit()
        return "inserted"
    except IntegrityError:
        session.rollback()
        return "skipped"

def bootstrap_db():
    # Use the comprehensive initialization that creates all tables including sources
    init_schema_and_seed_if_needed()
    
    # Additional seeding for API keys (this is now handled by init_schema_and_seed_if_needed)
    # but we keep the environment-specific key seeding here
    s = SessionLocal()
    try:
        if not s.query(Tenant).filter_by(tenant_id="default").one_or_none():
            s.add(Tenant(tenant_id="default", name="Default"))
            s.commit()

        admin_scopes = ["admin", "ingest", "read_metrics", "export", "manage_indicators"]
        user_scopes  = ["ingest", "read_metrics"]

        # Admin key(s)
        admin_token = os.getenv("API_KEY", "TEST_ADMIN_KEY")
        _upsert_key(s, "admin", admin_token, admin_scopes)

        # Additional admin keys (CI passes TELEMETRY_SEED_KEYS)
        extra = os.getenv("TELEMETRY_SEED_KEYS", "")
        for idx, tok in enumerate([t.strip() for t in extra.split(",") if t.strip()]):
            _upsert_key(s, f"admin_{idx+1}", tok, admin_scopes)

        # Non-admin user key used by tests
        user_token = os.getenv("USER_API_KEY", "***")
        _upsert_key(s, "user", user_token, user_scopes)

        log.info("DB_BOOT: seeded admin/user API keys")
    finally:
        s.close()
