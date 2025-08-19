import os, time
from typing import Optional

REDIS_URL = os.getenv("REDIS_URL")


class Cache:
    def __init__(self):
        self.r = None
        if REDIS_URL:
            import redis  # type: ignore
            self.r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

    def setnx_ttl(self, key: str, ttl: int) -> bool:
        if not self.r:
            # in-memory fallback (dev only)
            from threading import Lock
            _mem = getattr(self, "_mem", {})
            _lock = getattr(self, "_lock", Lock())
            with _lock:
                if key in _mem and _mem[key] > time.time():
                    return False
                _mem[key] = time.time() + ttl
                self._mem, self._lock = _mem, _lock
                return True
        return bool(self.r.set(key, "1", nx=True, ex=ttl))

    def incr_with_ttl(self, key: str, ttl: int) -> int:
        if not self.r:
            # simple fallback counter
            from threading import Lock
            _c = getattr(self, "_c", {})
            _t = getattr(self, "_t", {})
            _lock = getattr(self, "_cl", Lock())
            now = time.time()
            with _lock:
                if key not in _t or _t[key] < now:
                    _t[key] = now + ttl
                    _c[key] = 0
                _c[key] += 1
                self._c, self._t, self._cl = _c, _t, _lock
                return _c[key]
        p = self.r.pipeline()
        p.incr(key)
        p.expire(key, ttl)
        return int(p.execute()[0])


cache = Cache()


