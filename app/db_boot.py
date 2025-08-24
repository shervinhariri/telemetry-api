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

        env_keys = os.getenv("TELEMETRY_SEED_KEYS", "DEV_ADMIN_KEY_5a8f9ffdc3,TEST_ADMIN_KEY")
        tokens = [t.strip() for t in env_keys.split(",") if t.strip()]

        # ensure each token exists (idempotent)
        for tok in tokens:
            h = _sha(tok)
            db.execute(text("""
            INSERT INTO api_keys (key_id, tenant_id, hash, scopes, disabled, created_at)
            VALUES (:key_id, :tenant, :hash, :scopes, 0, :ts)
            ON CONFLICT(key_id) DO UPDATE SET hash=excluded.hash
            """), dict(
                key_id=f"seed-{h[:8]}",
                tenant="default",
                hash=h,
                scopes="admin,*",
                ts=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ))
        db.commit()

        res = db.execute(text("SELECT COUNT(*) FROM api_keys"))
        keys = int(list(res)[0][0])
        log.info("DB_BOOT: ensured schema; keys=%d (seeded=%d)", keys, len(tokens))
