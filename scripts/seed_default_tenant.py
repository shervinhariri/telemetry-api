#!/usr/bin/env python3
"""
Seed script to create default tenant and admin API key
"""
import os
import uuid
import hashlib
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.models.tenant import Tenant
from app.models.apikey import ApiKey

def hash_key(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()

if __name__ == "__main__":
    # Allow disabling seeding entirely (prod)
    if os.getenv("SEED_DEFAULT_TENANT", "1") in ("0", "false", "False"):
        print("Seeding disabled via SEED_DEFAULT_TENANT=0")
        raise SystemExit(0)

    db = SessionLocal()
    try:
        # Check/create default tenant
        default_tenant = db.query(Tenant).filter(Tenant.tenant_id == "default").first()
        if not default_tenant:
            print("Creating default tenant...")
            default_tenant = Tenant(tenant_id="default", name="Default Tenant", retention_days=7)
            db.add(default_tenant)
            db.commit()
            print("✓ Default tenant created")
        else:
            print("✓ Default tenant exists")

        # Check for existing admin key for default tenant
        existing_admin = None
        for k in db.query(ApiKey).filter(ApiKey.tenant_id == "default").all():
            try:
                if k.scopes and ("admin" in k.scopes):
                    existing_admin = k
                    break
            except Exception:
                pass

        if existing_admin:
            print("✓ Admin API key exists (not shown)")
            raise SystemExit(0)

        # No admin key yet: create one, optionally from bootstrap env (do not echo)
        bootstrap = os.getenv("ADMIN_BOOTSTRAP_KEY")
        if bootstrap and bootstrap.strip():
            secret = bootstrap.strip()
            show_secret = False  # never echo provided secret
        else:
            secret = "DEV_ADMIN_KEY_" + uuid.uuid4().hex[:10]
            show_secret = True

        key_id = "admin_" + uuid.uuid4().hex[:6]
        print("Creating admin API key...")
        key = ApiKey(
            key_id=key_id,
            tenant_id="default",
            hash=hash_key(secret),
            scopes=["admin", "ingest", "read_metrics", "export"]
        )
        db.add(key)
        db.commit()
        print("✓ Admin API key created")

        if show_secret:
            print("\n" + "=" * 50)
            print("ADMIN API KEY (copy now, shown once):")
            print(f"{secret}")
            print("=" * 50)
            print("\nUse this key with:")
            print(f"curl -H 'Authorization: Bearer {secret}' http://localhost/v1/health")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()
