# app/db_boot.py
import os, json, logging
from sqlalchemy.exc import IntegrityError
from .db import engine, Base, SessionLocal
from .models.tenant import Tenant
from .models.apikey import ApiKey
import hashlib

log = logging.getLogger("bootstrap")

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

DEFAULT_TENANT = "default"
ADMIN_KEY_ID = "admin"
USER_KEY_ID = "user"

ADMIN_SCOPES = ["admin", "ingest", "read_metrics", "export", "manage_indicators"]
USER_SCOPES  = ["ingest", "read_metrics"]  # no 'admin'

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
            key_id=key_id, tenant_id=DEFAULT_TENANT,
            hash=h, scopes=json.dumps(scopes), disabled=disabled
        ))
        session.commit()
        return "inserted"
    except IntegrityError:
        session.rollback()
        return "skipped"

def bootstrap_db():
    # 1) ensure tables
    Base.metadata.create_all(bind=engine)

    # 2) migrations (safe if present)
    try:
        import subprocess, sys
        subprocess.run([sys.executable, "/app/scripts/migrate_sqlite.py"], check=True)
        log.info("DB_BOOT: migrations applied")
    except Exception as e:
        log.info("DB_BOOT: migrations skipped: %s", e)

    # 3) upsert tenant + keys
    s = SessionLocal()
    try:
        tenant = s.query(Tenant).filter(Tenant.tenant_id == DEFAULT_TENANT).one_or_none()
        if not tenant:
            s.add(Tenant(tenant_id=DEFAULT_TENANT, name="Default"))
            s.commit()

        admin_token = os.getenv("API_KEY", "TEST_ADMIN_KEY")
        user_token  = os.getenv("USER_API_KEY", "***")

        ares = _upsert_key(s, ADMIN_KEY_ID, admin_token, ADMIN_SCOPES)
        ures = _upsert_key(s, USER_KEY_ID, user_token, USER_SCOPES)
        log.info("DB_BOOT: admin key %s; user key %s", ares, ures)
    finally:
        s.close()
