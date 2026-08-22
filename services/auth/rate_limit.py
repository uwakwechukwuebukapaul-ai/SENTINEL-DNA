"""Provider-neutral authentication rate-limit backends.

The local database backend is deterministic and suitable for one-process
development.  RedisRateLimitBackend documents the distributed contract without
adding a Redis dependency to the application.
"""
from datetime import datetime, timedelta, timezone
import hashlib


class RateLimitBackend:
    def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        raise NotImplementedError


class DatabaseRateLimitBackend(RateLimitBackend):
    def __init__(self, db):
        self.db = db

    def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        now = datetime.now(timezone.utc)
        key_hash = hashlib.sha256(str(key).encode()).hexdigest()
        with self.db.session() as connection:
            row = connection.execute("SELECT window_started,count FROM auth_rate_limits WHERE bucket_hash=?", (key_hash,)).fetchone()
            if not row or datetime.fromisoformat(row["window_started"]) + timedelta(seconds=window_seconds) <= now:
                connection.execute("INSERT OR REPLACE INTO auth_rate_limits(bucket_hash,window_started,count) VALUES(?,?,1)", (key_hash, now.isoformat()))
                return True
            if int(row["count"]) >= limit:
                return False
            connection.execute("UPDATE auth_rate_limits SET count=count+1 WHERE bucket_hash=?", (key_hash,))
            return True


class RedisRateLimitBackend(RateLimitBackend):
    """Adapter contract for a shared Redis client supplied by deployment code."""
    def __init__(self, client, *, prefix="sentinel:auth:rate:"):
        self.client = client
        self.prefix = prefix

    def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        redis_key = self.prefix + hashlib.sha256(str(key).encode()).hexdigest()
        count = int(self.client.incr(redis_key))
        if count == 1:
            self.client.expire(redis_key, window_seconds)
        return count <= limit
