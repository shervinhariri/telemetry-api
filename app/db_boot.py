# app/db_boot.py
import os, time, hashlib, logging
from sqlalchemy import text
from .db import SessionLocal

log = logging.getLogger("telemetry")



def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def ensure_schema_and_seed_keys():
    # 1) Ensure schema using ORM
    from app.db import Base, engine
    
    # Import all models to ensure they're registered with Base.metadata
    from app.models.tenant import Tenant
    from app.models.apikey import ApiKey
    from app.models.job import Job
    from app.models.output_config import OutputConfig
    
    Base.metadata.create_all(bind=engine)
    
    with SessionLocal() as db:
        # 2) Ensure default tenant exists
        db.execute(text("""
        INSERT OR IGNORE INTO tenants (tenant_id, name, retention_days, quotas, redaction)
        VALUES ('default', 'Default Tenant', 7, '{}', '{}')
        """))
        
        db.commit()

        # 3) Seed defaults if empty OR ensure presence of provided keys
        res = db.execute(text("SELECT COUNT(*) FROM api_keys"))
        count = int(list(res)[0][0])

        env_keys = os.getenv("TELEMETRY_SEED_KEYS", "TEST_ADMIN_KEY,DEV_ADMIN_KEY_5a8f9ffdc3")
        tokens = [t.strip() for t in env_keys.split(",") if t.strip()]

        # ensure each token exists (idempotent)
        for tok in tokens:
            h = _sha(tok)
            key_id = f"seed-{h[:8]}"
            scopes = '["admin","*"]'  # JSON array format
            
            db.execute(text("""
            INSERT INTO api_keys (key_id, tenant_id, hash, scopes, disabled, created_at)
            VALUES (:key_id, :tenant, :hash, :scopes, 0, :ts)
            ON CONFLICT(key_id) DO UPDATE SET hash=excluded.hash, scopes=excluded.scopes
            """), dict(
                key_id=key_id,
                tenant="default",
                hash=h,
                scopes=scopes,
                ts=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ))
            log.info("DB_BOOT: seeded key_id=%s scopes=%s", key_id, scopes)
        
        db.commit()

        # 4) Diagnostic: show what we have
        res = db.execute(text("SELECT key_id, scopes, disabled FROM api_keys"))
        keys = res.fetchall()
        log.info("DB_BOOT: ensured schema; total_keys=%d (seeded=%d)", len(keys), len(tokens))
        for key in keys[:2]:  # Show first 2 keys with their scopes
            log.info("DB_BOOT: key_id=%s scopes=%s disabled=%s", key[0], key[1], key[2])
        
        # 5) Auth hardening: assert admin keys exist
        admin_keys = [k for k in keys if '"admin"' in k[1] and k[2] == 0]
        if not admin_keys:
            raise RuntimeError("No active admin API keys found - system cannot start")
        
        # Log seeded key IDs (masked for security)
        seeded_key_ids = [f"{k[0][:4]}...{k[0][-4:]}" for k in admin_keys[:3]]
        log.info("DB_BOOT: admin keys available: %s", ", ".join(seeded_key_ids))
