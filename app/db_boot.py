# app/db_boot.py
import os, time, hashlib, logging
from sqlalchemy import text
from .db import SessionLocal

log = logging.getLogger("telemetry")

DDL_API_KEYS = """
CREATE TABLE IF NOT EXISTS api_keys (
  key_id TEXT PRIMARY KEY,
  tenant_id TEXT,
  hash TEXT,
  scopes TEXT,
  disabled INTEGER DEFAULT 0,
  created_at TEXT
)
"""

def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def ensure_schema_and_seed_keys():
    with SessionLocal() as db:
        # 1) Ensure schema
        db.execute(text(DDL_API_KEYS))
        db.commit()

        # 2) Seed defaults if empty OR ensure presence of provided keys
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

        # 3) Diagnostic: show what we have
        res = db.execute(text("SELECT key_id, scopes, disabled FROM api_keys"))
        keys = res.fetchall()
        log.info("DB_BOOT: ensured schema; total_keys=%d (seeded=%d)", len(keys), len(tokens))
        for key in keys[:2]:  # Show first 2 keys with their scopes
            log.info("DB_BOOT: key_id=%s scopes=%s disabled=%s", key[0], key[1], key[2])
