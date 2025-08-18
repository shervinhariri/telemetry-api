from datetime import datetime, timedelta
from pathlib import Path
from app.db import SessionLocal
from app.models.tenant import Tenant
from app.services.paths import events_path
import os

def cleanup_old_events(tenant_id: str):
    with SessionLocal() as db:
        t = db.get(Tenant, tenant_id)
        days = t.retention_days if t and t.retention_days else 7
    cutoff = datetime.utcnow() - timedelta(days=days)
    root: Path = events_path(tenant_id)
    for f in root.glob("*.ndjson"):
        if datetime.utcfromtimestamp(f.stat().st_mtime) < cutoff:
            try: 
                os.remove(f)
            except: 
                pass
