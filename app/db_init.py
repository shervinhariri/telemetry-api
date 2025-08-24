from typing import Iterable, Tuple
from threading import Lock

from .db import Base, engine, SessionLocal
from .utils.crypto import hash_token

# Import your ApiKey SQLAlchemy model (adjust the path if needed)
from .models.apikey import ApiKey
from .models.tenant import Tenant

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
        # 1) Ensure tables exist
        Base.metadata.create_all(bind=engine)
        # 2) Seed keys if table empty
        with SessionLocal() as s:
            try:
                count = s.query(ApiKey).count()
            except Exception:
                # If the table wasn't created for any reason, try again then re-count
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
                        hash=hash_token(token),
                        scopes=scopes.split(','),
                        disabled=False,
                    ))
                s.commit()
        _initialized = True
