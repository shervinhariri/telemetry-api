import os
import json
import hashlib
from sqlalchemy.orm import Session
from .db import Base
from .models.tenant import Tenant
from .models.apikey import ApiKey

DEFAULT_KEY = os.getenv("API_KEY", "TEST_ADMIN_KEY")

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def bootstrap_db(engine) -> None:
    """Create tables and seed default tenant + API key. Idempotent."""
    Base.metadata.create_all(bind=engine)
    with Session(bind=engine) as s:
        # tenant
        tenant = s.query(Tenant).filter_by(tenant_id="default").first()
        if not tenant:
            tenant = Tenant(tenant_id="default", name="Default")
            s.add(tenant)
            s.flush()

        # api key
        token_hash = _hash_token(DEFAULT_KEY)
        key = s.query(ApiKey).filter_by(hash=token_hash).first()
        if not key:
            scopes = ["admin", "ingest", "read_metrics", "export", "manage_indicators"]
            key = ApiKey(
                key_id="admin",
                tenant_id=tenant.tenant_id,
                hash=token_hash,
                scopes=json.dumps(scopes),
                disabled=False,
            )
            s.add(key)

        # sanitize legacy non-JSON scopes if any
        # keep try/except to avoid failures on first boot
        try:
            for k in s.query(ApiKey).all():
                if isinstance(k.scopes, str):
                    try:
                        json.loads(k.scopes)
                    except Exception:
                        k.scopes = json.dumps(["admin", "ingest", "read_metrics"])
        except Exception:
            pass

        s.commit()
