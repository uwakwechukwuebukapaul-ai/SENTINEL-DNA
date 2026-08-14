from __future__ import annotations
import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

class ObservabilityService:
    def __init__(self, logger: logging.Logger | None = None): self.logger = logger or logging.getLogger("sentinel_dna")
    def event(self, name: str, **fields: Any) -> None:
        """Emit a safe structured event; telemetry failures never affect callers."""
        try:
            blocked = {"password", "password_hash", "secret", "token", "api_key"}
            safe = {key: value for key, value in fields.items() if key.lower() not in blocked and not key.lower().endswith("_token")}
            safe.setdefault("event_id", str(uuid.uuid4()))
            safe.setdefault("timestamp", time.time())
            safe.setdefault("correlation_id", safe.get("correlation_id") or "unknown")
            safe.setdefault("tenant_id", safe.get("tenant_id") or "unknown")
            self.logger.info("%s", {"event": name, **safe})
        except Exception:
            return None
    def metric(self, name: str, value: Any = 1, **fields: Any) -> None: self.event(name, value=value, **fields)
    @contextmanager
    def measure(self, name: str, **fields: Any) -> Iterator[None]:
        started = time.perf_counter()
        try: yield
        except Exception as exc:
            self.logger.exception("%s", {"event": name, "error": type(exc).__name__, **fields})
            raise
        finally: self.event(name, duration_ms=round((time.perf_counter() - started) * 1000, 2), **fields)
