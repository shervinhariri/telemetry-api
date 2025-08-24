from typing import Iterable, Tuple
from threading import Lock
from sqlalchemy.exc import OperationalError

from .db import Base, engine, SessionLocal
from .utils.crypto import hash_token

_DEFAULT_KEYS: Iterable[Tuple[str, str, str]] = [
    ("TEST_KEY", "tenant-default", "ingest,read"),
    ("TEST_ADMIN_KEY", "tenant-default", "admin,ingest,read"),
]

_initialized = False
_init_lock = Lock()

RAW_API_KEYS_DDL = """
CREATE TABLE IF NOT EXISTS api_keys (
  key_id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id VARCHAR(255) NOT NULL,
  hash VARCHAR(128) NOT NULL UNIQUE,
  scopes VARCHAR(255) NOT NULL,
  disabled BOOLEAN NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

def _raw_create_api_keys_table_and_seed() -> None:
    # Create table if not exists (works even if ORM model wasn't imported)
    with engine.begin() as conn:
        conn.exec_driver_sql(RAW_API_KEYS_DDL)
        # Check row count
        cnt = conn.exec_driver_sql("SELECT COUNT(*) FROM api_keys").scalar()
        if cnt == 0:
            for token, tenant_id, scopes in _DEFAULT_KEYS:
                conn.exec_driver_sql(
                    "INSERT INTO api_keys (tenant_id, hash, scopes, disabled) VALUES (?, ?, ?, 0)",
                    (tenant_id, hash_token(token), scopes),
                )

def init_schema_and_seed_if_needed() -> None:
    """
    Ensure DB schema exists and seed default API keys.
    1) Try ORM create_all (no-op if metadata is incomplete).
    2) Always run raw DDL to guarantee api_keys exists.
    3) Seed when empty.
    Safe to call multiple times.
    """
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        # Try ORM path first for other tables
        try:
            Base.metadata.create_all(bind=engine)
        except Exception:
            pass

        # Hard guarantee api_keys table exists and is seeded
        _raw_create_api_keys_table_and_seed()

        _initialized = True
