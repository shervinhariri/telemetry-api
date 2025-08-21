# scripts/bootstrap.py
import os, hashlib, time, sys
sys.path.insert(0, '/app')
from sqlalchemy.orm import sessionmaker
from app.db import engine, Base
from app.models.tenant import Tenant
from app.models.apikey import ApiKey

ADMIN_KEY = os.getenv("BOOTSTRAP_ADMIN_API_KEY", "DEV_ADMIN_KEY_localdev")
DEFAULT_TENANT_ID = os.getenv("BOOTSTRAP_TENANT_ID", "default")

def run():
    # 1) create/upgrade schema
    Base.metadata.create_all(bind=engine)

    # 2) seed tenant + admin key if missing
    Session = sessionmaker(bind=engine)
    s = Session()
    t = s.query(Tenant).filter_by(tenant_id=DEFAULT_TENANT_ID).one_or_none()
    if not t:
        t = Tenant(tenant_id=DEFAULT_TENANT_ID, name="Default Tenant")
        s.add(t); s.commit()

    h = hashlib.sha256(ADMIN_KEY.encode()).hexdigest()
    k = s.query(ApiKey).filter_by(key_id="admin", tenant_id=DEFAULT_TENANT_ID).one_or_none()
    if not k:
        k = ApiKey(key_id="admin", tenant_id=DEFAULT_TENANT_ID, hash=h,
                   scopes=["admin","ingest","read_metrics","export","manage_indicators"])
        s.add(k); s.commit()
    else:
        # keep the same key_id; only update if empty hash
        if not k.hash:
            k.hash = h; s.commit()
    s.close()

if __name__ == "__main__":
    run()
