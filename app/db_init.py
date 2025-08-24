from typing import Iterable, Tuple
from .db import Base, engine, session_scope
from .auth.deps import _hash  # already exists in your repo
from .models.apikey import ApiKey  # adjust import if your model path differs
from .models.tenant import Tenant  # for foreign key constraint

DEFAULT_KEYS: Iterable[Tuple[str, str, str]] = [
    ("TEST_KEY", "tenant-default", "ingest,read"),
    ("TEST_ADMIN_KEY", "tenant-default", "admin,ingest,read"),
]

def init_schema_and_seed() -> None:
    """
    Ensure DB schema exists and seed default API keys if table is empty.
    Safe to call multiple times.
    """
    # 1) Create tables if they do not exist
    Base.metadata.create_all(bind=engine)

    # 2) Seed default tenant if empty
    with session_scope() as s:
        tenant_count = s.query(Tenant).count()
        if tenant_count == 0:
            s.add(Tenant(
                tenant_id="tenant-default",
                name="Default Tenant",
                retention_days=7,
                quotas={"eps": 600, "batch_max": 10000, "dlq_max": 100000},
                redaction={"fields": []}
            ))
    
    # 3) Seed API keys if empty
    with session_scope() as s:
        count = s.query(ApiKey).count()
        if count == 0:
            for token, tenant_id, scopes in DEFAULT_KEYS:
                # Generate a key_id for the API key
                import uuid
                key_id = str(uuid.uuid4()).replace('-', '')[:32]
                
                s.add(ApiKey(
                    key_id=key_id,
                    tenant_id=tenant_id,
                    hash=_hash(token),
                    scopes=scopes.split(','),
                    disabled=False,
                ))
