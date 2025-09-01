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
    row = session.query(ApiKey).filter_by(key_id=key_id).one_or_none()
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

def _ensure_sources_table():
    """Direct fallback to ensure sources table exists"""
    try:
        with engine.begin() as conn:
            # Check if sources table exists
            result = conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table' AND name='sources'").fetchone()
            if not result:
                log.info("Creating sources table directly")
                # Create sources table with minimal schema
                conn.exec_driver_sql("""
                    CREATE TABLE sources (
                        id VARCHAR(64) PRIMARY KEY,
                        tenant_id VARCHAR(64) NOT NULL,
                        type VARCHAR(32) NOT NULL,
                        origin VARCHAR(32),
                        display_name VARCHAR(128) NOT NULL,
                        collector VARCHAR(64) NOT NULL,
                        site VARCHAR(64),
                        tags TEXT,
                        health_status VARCHAR(32) DEFAULT 'stale',
                        last_seen TIMESTAMP,
                        notes TEXT,
                        status VARCHAR(32) NOT NULL DEFAULT 'enabled',
                        allowed_ips TEXT NOT NULL DEFAULT '[]',
                        max_eps INTEGER NOT NULL DEFAULT 0,
                        block_on_exceed BOOLEAN NOT NULL DEFAULT 1,
                        enabled BOOLEAN NOT NULL DEFAULT 1,
                        eps_cap INTEGER NOT NULL DEFAULT 0,
                        last_seen_ts INTEGER,
                        eps_1m REAL,
                        error_pct_1m REAL,
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL
                    )
                """)
                
                # Insert default sources
                import time
                now = int(time.time())
                default_sources = [
                    ("default-http", "default", "http", "http", "Default HTTP Source", "api", "HQ", "[]", "healthy", None, "Default HTTP ingest source", "enabled", "[]", 0, 1, 1, 0, now, 0.0, 0.0, now, now),
                    ("default-udp", "default", "udp", "udp", "Default UDP Source", "udp_head", "HQ", "[]", "healthy", None, "Default UDP ingest source", "enabled", "[]", 0, 1, 1, 0, now, 0.0, 0.0, now, now)
                ]
                
                for source_data in default_sources:
                    conn.exec_driver_sql("""
                        INSERT INTO sources (
                            id, tenant_id, type, origin, display_name, collector, site, tags, 
                            health_status, last_seen, notes, status, allowed_ips, max_eps, 
                            block_on_exceed, enabled, eps_cap, last_seen_ts, eps_1m, 
                            error_pct_1m, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, source_data)
                
                log.info("Sources table created and seeded with default sources")
            else:
                log.info("Sources table already exists")
    except Exception as e:
        log.error(f"Failed to ensure sources table: {e}")

def bootstrap_db():
    # Use the comprehensive initialization that creates all tables including sources
    try:
        init_schema_and_seed_if_needed()
        log.info("DB_BOOT: comprehensive initialization completed")
    except Exception as e:
        log.warning(f"Comprehensive initialization failed: {e}, using fallback")
        # Fallback: ensure basic tables exist
        Base.metadata.create_all(bind=engine)
        _ensure_sources_table()
    
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
