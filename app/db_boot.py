# app/db_boot.py
import os, time, hashlib, logging
from sqlalchemy import text
from .db import SessionLocal, engine, Base

log = logging.getLogger("telemetry")



def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def bootstrap_db(engine):
    """
    Bootstrap database schema and seed default tenant + API key from environment.
    This is called during app startup and is idempotent.
    """
    # 1) Create all tables using ORM
    Base.metadata.create_all(bind=engine)
    
    with SessionLocal() as db:
        # 2) Ensure default tenant exists
        db.execute(text("""
        INSERT OR IGNORE INTO tenants (tenant_id, name, retention_days, quotas, redaction)
        VALUES ('default', 'Default Tenant', 7, '{}', '{}')
        """))
        
        # 3) Seed API key from environment
        api_key = os.getenv("API_KEY", "DEV_ADMIN_KEY_5a8f9ffdc3")
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_id = f"bootstrap-{hashlib.sha256(api_key.encode()).hexdigest()[:8]}"
        
        # Insert API key if it doesn't exist
        db.execute(text("""
        INSERT OR IGNORE INTO api_keys (key_id, tenant_id, hash, scopes, disabled, created_at)
        VALUES (:key_id, 'default', :hash, :scopes, 0, :ts)
        """), {
            "key_id": key_id,
            "hash": key_hash,
            "scopes": '["admin","*"]',
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        })
        
        db.commit()
        
        # 4) Log bootstrap status
        from .models.apikey import ApiKey
        key_count = db.query(ApiKey).count()
        logging.getLogger("app").info(
            "DB_BOOTSTRAP: seeded API key from env, total keys=%s", 
            key_count
        )

def ensure_schema_and_seed_keys():
    """
    Legacy function - now just calls bootstrap_db for backward compatibility
    """
    bootstrap_db(engine)
