import os
from .cache import cache

PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "600"))


def check_limit(tenant_id: str, api_key_id: str) -> bool:
    key_k = f"rl:key:{api_key_id}"
    key_t = f"rl:tenant:{tenant_id}"
    c1 = cache.incr_with_ttl(key_k, 60)
    c2 = cache.incr_with_ttl(key_t, 60)
    return c1 <= PER_MIN and c2 <= PER_MIN


