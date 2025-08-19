import hashlib
import os
from .cache import cache

TTL = int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "86400"))


def batch_hash(tenant_id: str, api_key_id: str, payload: bytes) -> str:
    h = hashlib.sha256()
    h.update(tenant_id.encode())
    h.update(api_key_id.encode())
    h.update(payload)
    return "idem:" + h.hexdigest()


def seen_or_store(tenant_id: str, api_key_id: str, payload: bytes) -> bool:
    k = batch_hash(tenant_id, api_key_id, payload)
    ok = cache.setnx_ttl(k, TTL)  # True if stored new
    return not ok  # True if already seen


