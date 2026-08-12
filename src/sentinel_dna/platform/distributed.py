"""Redis-backed distributed primitives with explicit tenant-safe key namespaces."""
from __future__ import annotations
import json
from hashlib import sha256
from threading import Lock
from time import monotonic
from typing import Any, Protocol

class RateLimitStore(Protocol):
    def allow(self, key: str, limit: int, window_seconds: int) -> bool: ...

def _key(namespace: str, value: str) -> str:
    return f"sentinel-dna:{namespace}:{sha256(value.encode()).hexdigest()}"

class LocalRateLimitStore:
    def __init__(self) -> None: self._entries: dict[str, tuple[float, int]] = {}; self._lock = Lock()
    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        if limit <= 0: return True
        now = monotonic()
        with self._lock:
            started, count = self._entries.get(key, (now, 0))
            if now - started >= window_seconds: started, count = now, 0
            if count >= limit: return False
            self._entries[key] = (started, count + 1); return True

class RedisRateLimitStore:
    """Atomic INCR + expiry rate limit; accepts a client for tested dependency injection."""
    def __init__(self, redis_url: str, client=None) -> None:
        if not redis_url.startswith(("redis://", "rediss://")): raise ValueError("Redis URL is required")
        if client is None:
            try:
                import redis
                client = redis.Redis.from_url(redis_url, decode_responses=True)
            except ImportError as exc: raise RuntimeError("Redis support requires sentinel-dna[redis]") from exc
        self.client = client
    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        if limit <= 0: return True
        name = _key("rate", key)
        pipe = self.client.pipeline(transaction=True)
        pipe.incr(name); pipe.expire(name, window_seconds, nx=True)
        count, _ = pipe.execute()
        return int(count) <= limit

class RedisCache:
    def __init__(self, redis_url: str, client=None) -> None:
        self._redis = RedisRateLimitStore(redis_url, client).client
    def get(self, tenant_id: str, name: str) -> Any | None:
        raw = self._redis.get(_key(f"cache:{tenant_id}", name))
        return json.loads(raw) if raw else None
    def set(self, tenant_id: str, name: str, value: Any, ttl_seconds: int) -> None:
        if ttl_seconds <= 0: raise ValueError("cache TTL must be positive")
        self._redis.set(_key(f"cache:{tenant_id}", name), json.dumps(value), ex=ttl_seconds)

class RedisSessionStore:
    """Optional distributed session mirror; authoritative revocation remains in SaaS DB."""
    def __init__(self, redis_url: str, client=None) -> None: self._redis = RedisRateLimitStore(redis_url, client).client
    def put(self, token_digest: str, user_id: str, ttl_seconds: int) -> None:
        self._redis.set(_key("session", token_digest), user_id, ex=ttl_seconds)
    def get(self, token_digest: str) -> str | None: return self._redis.get(_key("session", token_digest))
    def revoke(self, token_digest: str) -> None: self._redis.delete(_key("session", token_digest))
