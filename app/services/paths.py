from pathlib import Path

DATA_ROOT = Path("/data")

def tenant_root(tenant_id: str) -> Path:
    p = DATA_ROOT / "tenants" / tenant_id
    p.mkdir(parents=True, exist_ok=True)
    return p

def events_path(tenant_id: str) -> Path:
    p = tenant_root(tenant_id) / "events"
    p.mkdir(exist_ok=True)
    return p

def dlq_path(tenant_id: str) -> Path:
    p = tenant_root(tenant_id) / "dlq"
    p.mkdir(exist_ok=True)
    return p

def logs_path(tenant_id: str) -> Path:
    p = tenant_root(tenant_id) / "logs"
    p.mkdir(exist_ok=True)
    return p
