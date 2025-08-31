# app/db_boot.py
import os
import json
import hashlib
from sqlalchemy.orm import Session
from sqlalchemy.sql.sqltypes import String
from .db import Base
from .models.tenant import Tenant
from .models.apikey import ApiKey

DEFAULT_KEY = os.getenv("API_KEY", "TEST_ADMIN_KEY")

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def _make_scopes_value(scopes_list, is_text_column: bool):
    # Store as JSON string only if the column is TEXT; otherwise keep list
    return json.dumps(scopes_list) if is_text_column else scopes_list

def bootstrap_db(engine) -> None:
    """
    Create tables and upsert default tenant + admin key.
    - If 'admin' key exists, UPDATE hash/scopes/disabled.
    - If missing, INSERT a new one.
    Safe to run on every startup.
    """
    Base.metadata.create_all(bind=engine)

    desired_scopes = ["admin", "ingest", "read_metrics", "export", "manage_indicators"]
    desired_hash = _hash_token(DEFAULT_KEY)

    is_scopes_text = isinstance(ApiKey.__table__.c.scopes.type, String)
    scopes_value = _make_scopes_value(desired_scopes, is_scopes_text)

    with Session(bind=engine) as s:
        try:
            # ensure tenant
            tenant = s.query(Tenant).filter_by(tenant_id="default").one_or_none()
            if tenant is None:
                tenant = Tenant(tenant_id="default", name="Default")
                s.add(tenant)
                s.flush()

            # UPSERT admin key by key_id
            key = s.query(ApiKey).filter_by(key_id="admin").one_or_none()
            if key is None:
                key = ApiKey(
                    key_id="admin",
                    tenant_id=tenant.tenant_id,
                    hash=desired_hash,
                    scopes=scopes_value,
                    disabled=False,
                )
                s.add(key)
            else:
                key.hash = desired_hash
                key.disabled = False
                # normalize scopes to the right shape
                if is_scopes_text:
                    # If DB has JSON string already, keep; else set fresh
                    try:
                        # If it's a string that parses to list, keep existing + merge admin perms
                        existing = json.loads(key.scopes) if isinstance(key.scopes, str) else []
                        if not isinstance(existing, list):
                            existing = []
                        merged = sorted(set(existing + desired_scopes))
                        key.scopes = json.dumps(merged)
                    except Exception:
                        key.scopes = json.dumps(desired_scopes)
                else:
                    # JSON column
                    if not isinstance(key.scopes, list):
                        key.scopes = desired_scopes
                    else:
                        merged = sorted(set(key.scopes + desired_scopes))
                        key.scopes = merged

            s.commit()

        except Exception:
            s.rollback()
            # last-resort: try update-only path (handles "UNIQUE constraint" on prior insert)
            try:
                key = s.query(ApiKey).filter_by(key_id="admin").one_or_none()
                if key is not None:
                    key.hash = desired_hash
                    key.disabled = False
                    key.scopes = scopes_value
                    s.commit()
                else:
                    # if still not there, insert once more
                    key = ApiKey(
                        key_id="admin",
                        tenant_id="default",
                        hash=desired_hash,
                        scopes=scopes_value,
                        disabled=False,
                    )
                    s.add(key)
                    s.commit()
            except Exception:
                s.rollback()
                raise
