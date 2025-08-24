# app/db_init.py
from typing import Iterable, Tuple
from threading import Lock

from .db import Base, engine, SessionLocal

# We deliberately import models *via a helper* so Base.metadata knows all tables.
# Cursor: implement import_all_models() to import every module that defines SQLAlchemy models.
def import_all_models() -> None:
    """
    Import all model modules so Declarative Base metadata is populated before create_all.
    Adjust the import list below to match your repo layout.
    """
    # Try common locations; Cursor will verify and adjust:
    try:
        import app.models  # if you have an __init__.py that imports all submodules
    except Exception:
        pass

    # Import known modules that define tables (Cursor: search and add as needed)
    try:
        import app.models.apikey  # contains ApiKey ( __tablename__ == 'api_keys' )
    except Exception:
        pass
    try:
        import app.models.tenant  # contains Tenant ( __tablename__ == 'tenants' )
    except Exception:
        pass
    try:
        import app.models.source  # contains Source ( __tablename__ == 'sources' )
    except Exception:
        pass
    try:
        import app.models.job  # contains Job ( __tablename__ == 'jobs' )
    except Exception:
        pass
    try:
        import app.models.output_config  # contains OutputConfig ( __tablename__ == 'output_configs' )
    except Exception:
        pass
    try:
        import app.models.admin_audit  # contains AdminAuditLog ( __tablename__ == 'admin_audit_logs' )
    except Exception:
        pass
    # Import models from app.db.models as well
    try:
        import app.db.models  # contains events, requests_audit, outputs, idempotency_keys
    except Exception:
        pass


def _hash_token(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()


# Import the ApiKey class for seeding (Cursor: fix this import to the correct module)
def _get_apikey_class():
    # Prefer direct import; fallback to resolving from Base registry.
    try:
        from app.models.apikey import ApiKey  # adjust if needed
        return ApiKey
    except Exception:
        # Fallback: find the mapped class by table name from Base
        for mapper in Base.registry.mappers:
            cls = mapper.class_
            if getattr(getattr(cls, "__table__", None), "name", None) == "api_keys":
                return cls
        raise ImportError("ApiKey model not found; ensure app.models.apikey is imported.")


_DEFAULT_KEYS: Iterable[Tuple[str, str, str]] = [
    ("TEST_KEY", "tenant-default", "ingest,read"),
    ("TEST_ADMIN_KEY", "tenant-default", "admin,ingest,read"),
]

_initialized = False
_init_lock = Lock()

def init_schema_and_seed_if_needed() -> None:
    """
    Ensure DB schema exists and seed default API keys if table is empty.
    Safe to call multiple times; guarded to run once per process.
    """
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return

        # 1) Import models first so metadata is complete.
        import_all_models()

        # 2) Create tables if missing.
        Base.metadata.create_all(bind=engine)

        # 3) Seed default API keys if table empty.
        ApiKey = _get_apikey_class()
        with SessionLocal() as s:
            try:
                count = s.query(ApiKey).count()
            except Exception:
                # If race or metadata lagged, retry once.
                Base.metadata.create_all(bind=engine)
                count = s.query(ApiKey).count()
            if count == 0:
                for token, tenant_id, scopes in _DEFAULT_KEYS:
                    # Generate a key_id for the API key
                    import uuid
                    key_id = str(uuid.uuid4()).replace('-', '')[:32]
                    
                    s.add(ApiKey(
                        key_id=key_id,
                        tenant_id=tenant_id,
                        hash=_hash_token(token),
                        scopes=scopes.split(','),
                        disabled=False,
                    ))
                s.commit()

        _initialized = True
