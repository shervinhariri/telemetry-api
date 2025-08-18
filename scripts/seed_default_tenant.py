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
    db = SessionLocal()
    try:
        # Check if default tenant exists
        if not db.query(Tenant).filter(Tenant.tenant_id == "default").first():
            print("Creating default tenant...")
            db.add(Tenant(tenant_id="default", name="Default Tenant", retention_days=7))
            db.commit()
            print("✓ Default tenant created")
        else:
            print("✓ Default tenant already exists")
        
        # Create admin API key
        secret = os.environ.get("ADMIN_API_KEY", "DEV_ADMIN_KEY_" + uuid.uuid4().hex[:10])
        key_id = "admin_" + uuid.uuid4().hex[:6]
        
        # Check if admin key already exists
        existing_key = db.query(ApiKey).filter(ApiKey.key_id == key_id).first()
        if not existing_key:
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
        else:
            print("✓ Admin API key already exists")
        
        print("\n" + "="*50)
        print("ADMIN API KEY (copy now, shown once):")
        print(f"{secret}")
        print("="*50)
        print("\nUse this key with:")
        print(f"curl -H 'Authorization: Bearer {secret}' http://localhost/v1/health")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()
