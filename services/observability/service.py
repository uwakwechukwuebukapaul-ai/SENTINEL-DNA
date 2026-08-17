from __future__ import annotations
import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator


_SENSITIVE_KEY_PARTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "authorization",
    "cookie",
    "credential",
    "raw_response",
    "provider_response",
    "email_body",
    "evidence_payload",
    "raw_body",
    "raw_payload",
)


def _safe_fields(fields: dict[str, Any]) -> dict[str, Any]:
    """Keep observability metadata structured without copying sensitive data."""
    def sanitize(key: str, value: Any) -> Any:
        lowered = key.lower()
        if lowered in {"error", "errors", "exception", "traceback", "message"} or any(part in lowered for part in _SENSITIVE_KEY_PARTS):
            return "[redacted]"
        if isinstance(value, dict):
            return {str(child_key): sanitize(str(child_key), child_value) for child_key, child_value in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [sanitize(key, item) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return type(value).__name__

    return {str(key): sanitize(str(key), value) for key, value in fields.items()}


class ObservabilityService:
    def __init__(self, logger: logging.Logger | None = None): self.logger = logger or logging.getLogger("sentinel_dna")
    def event(self, name: str, **fields: Any) -> None:
        """Emit a safe structured event; telemetry failures never affect callers."""
        try:
            safe = _safe_fields(fields)
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
            self.logger.error("%s", {"event": name, "error_type": type(exc).__name__, **_safe_fields(fields)})
            raise
        finally: self.event(name, duration_ms=round((time.perf_counter() - started) * 1000, 2), **fields)
