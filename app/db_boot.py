# app/db_boot.py
import os, json, hashlib, logging, subprocess, sys
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import engine, Base, SessionLocal
from .models.tenant import Tenant
from .models.apikey import ApiKey

log = logging.getLogger("bootstrap")

ADMIN_KEY_ID = "admin"
DEFAULT_TENANT = "default"
DEFAULT_SCOPES = ["admin","ingest","read_metrics","export","manage_indicators"]

def _sha256(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _migrate_sqlite():
    # if you have scripts/migrate_sqlite.py in container
    try:
        subprocess.run(
            [sys.executable, "/app/scripts/migrate_sqlite.py"],
            check=True,
            capture_output=True,
            text=True
        )
        log.info("DB_BOOT: migrate_sqlite.py completed")
    except Exception as e:
        log.warning("DB_BOOT: migrate_sqlite.py not run or failed: %s", e)

def _sanitize_scopes(session: Session):
    try:
        # Convert non-JSON scopes to JSON array strings once
        keys = session.query(ApiKey).all()
        touched = 0
        for k in keys:
            raw = k.scopes
            try:
                if isinstance(raw, list):
                    continue
                if isinstance(raw, str):
                    json.loads(raw)  # already JSON?
                    continue
            except Exception:
                pass
            # force-json
            k.scopes = json.dumps(DEFAULT_SCOPES if not raw else [raw] if isinstance(raw, str) else DEFAULT_SCOPES)
            touched += 1
        if touched:
            session.commit()
            log.info("DB_BOOT: sanitized %d key scopes to JSON lists", touched)
        else:
            log.info("DB_BOOT: scopes already normalized")
    except Exception as e:
        log.warning("DB_BOOT: scope sanitize skipped: %s", e)

def _seed_admin(session: Session):
    token = os.getenv("API_KEY", "TEST_ADMIN_KEY")
    h = _sha256(token)

    # ensure default tenant
    tenant = session.query(Tenant).filter(Tenant.tenant_id == DEFAULT_TENANT).one_or_none()
    if not tenant:
        tenant = Tenant(tenant_id=DEFAULT_TENANT, name="Default")
        session.add(tenant)
        session.commit()

    key = session.query(ApiKey).filter(ApiKey.key_id == ADMIN_KEY_ID).one_or_none()
    if key:
        # update hash & scopes if needed
        key.hash = h
        key.scopes = json.dumps(DEFAULT_SCOPES)
        key.disabled = False
        session.commit()
        log.info("DB_BOOT: admin key refreshed")
    else:
        try:
            session.add(ApiKey(
                key_id=ADMIN_KEY_ID,
                tenant_id=DEFAULT_TENANT,
                hash=h,
                scopes=json.dumps(DEFAULT_SCOPES),
                disabled=False
            ))
            session.commit()
            log.info("DB_BOOT: admin key inserted")
        except IntegrityError:
            session.rollback()
            log.info("DB_BOOT: admin key existed, refreshed instead")
            _seed_admin(session)  # retry as refresh

def bootstrap_db():
    # 1) create tables
    Base.metadata.create_all(bind=engine)
    # 2) run migrations (safe to run repeatedly)
    _migrate_sqlite()
    # 3) normalize scopes
    session = SessionLocal()
    try:
        _sanitize_scopes(session)
        # 4) seed/refresh admin
        _seed_admin(session)
    finally:
        session.close()
