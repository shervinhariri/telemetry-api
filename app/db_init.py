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

RAW_TENANTS_DDL = """
CREATE TABLE IF NOT EXISTS tenants (
  tenant_id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  retention_days INTEGER NOT NULL,
  quotas TEXT NOT NULL,
  redaction TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

RAW_API_KEYS_DDL = """
CREATE TABLE IF NOT EXISTS api_keys (
  key_id VARCHAR(32) PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL,
  hash VARCHAR(128) NOT NULL UNIQUE,
  scopes TEXT NOT NULL,
  disabled BOOLEAN NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
);
"""

def _raw_create_api_keys_table_and_seed() -> None:
    # Create table if not exists (works even if ORM model wasn't imported)
    with engine.begin() as conn:
        # Create tenants table first
        conn.exec_driver_sql(RAW_TENANTS_DDL)
        
        # Ensure default tenant exists
        conn.exec_driver_sql(
            "INSERT OR IGNORE INTO tenants (tenant_id, name, retention_days, quotas, redaction) VALUES (?, ?, ?, ?, ?)",
            ("default", "Default Tenant", 7, "{}", "{}")
        )
        
        # Create api_keys table
        conn.exec_driver_sql(RAW_API_KEYS_DDL)
        
        # Migrate sources table if it exists but is missing columns
        try:
            # Check if sources table exists
            result = conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table' AND name='sources'").fetchone()
            if result:
                # Add missing columns to sources table
                columns_to_add = [
                    ("origin", "VARCHAR"),
                    ("enabled", "BOOLEAN DEFAULT 1"),
                    ("eps_cap", "INTEGER DEFAULT 0"),
                    ("last_seen_ts", "INTEGER"),
                    ("eps_1m", "REAL"),
                    ("error_pct_1m", "REAL"),
                    ("created_at", "INTEGER"),
                    ("updated_at", "INTEGER")
                ]
                
                for col_name, col_type in columns_to_add:
                    try:
                        conn.exec_driver_sql(f"ALTER TABLE sources ADD COLUMN {col_name} {col_type}")
                    except Exception:
                        # Column might already exist, ignore
                        pass
        except Exception:
            # Sources table might not exist, ignore
            pass
        
        # Check row count
        cnt = conn.exec_driver_sql("SELECT COUNT(*) FROM api_keys").scalar()
        if cnt == 0:
            for token, tenant_id, scopes in _DEFAULT_KEYS:
                # Generate key_id from token hash
                import hashlib
                key_id = f"seed-{hashlib.sha256(token.encode()).hexdigest()[:8]}"
                # Convert scopes to JSON format
                scopes_json = f'["{",".join(scopes.split(","))}"]'
                conn.exec_driver_sql(
                    "INSERT INTO api_keys (key_id, tenant_id, hash, scopes, disabled) VALUES (?, ?, ?, ?, 0)",
                    (key_id, tenant_id, hash_token(token), scopes_json),
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
        
        # Import all models to ensure they're registered with Base.metadata
        from app.models.tenant import Tenant
        from app.models.apikey import ApiKey
        from app.models.job import Job
        from app.models.output_config import OutputConfig
        from app.models.source import Source
        
        # Try ORM path first for all tables
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            print(f"Warning: ORM create_all failed: {e}")

        # Hard guarantee api_keys table exists and is seeded
        _raw_create_api_keys_table_and_seed()

        _initialized = True
