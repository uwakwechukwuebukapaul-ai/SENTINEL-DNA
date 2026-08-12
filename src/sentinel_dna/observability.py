"""Small, dependency-free observability primitives for the service boundary."""

from __future__ import annotations

import json
import logging
from collections import Counter
from threading import Lock


class JsonFormatter(logging.Formatter):
    """Emit only allow-listed fields so request logs cannot leak secrets."""

    def format(self, record: logging.LogRecord) -> str:
        event = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("event_type", "method", "path", "status_code", "duration_ms"):
            value = getattr(record, field, None)
            if value is not None:
                event[field] = value
        return json.dumps(event, sort_keys=True, default=str)


def configure_logging() -> None:
    root = logging.getLogger("sentinel_dna")
    if root.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    root.propagate = False


class ServiceMetrics:
    """Thread-safe counters exposed in Prometheus text format without a dependency."""

    def __init__(self) -> None:
        self._requests: Counter[tuple[str, int]] = Counter()
        self._investigations: Counter[str] = Counter()
        self._investigation_duration_ms = 0.0
        self._lock = Lock()

    def record_request(self, method: str, status_code: int) -> None:
        with self._lock:
            self._requests[(method.upper(), status_code)] += 1

    def record_investigation(self, status: str, duration_ms: float) -> None:
        with self._lock:
            self._investigations[status] += 1
            self._investigation_duration_ms += max(0.0, duration_ms)

    def prometheus(self) -> str:
        with self._lock:
            lines = ["# HELP sentinel_dna_http_requests_total HTTP requests handled by the service.", "# TYPE sentinel_dna_http_requests_total counter"]
            lines.extend(
                f'sentinel_dna_http_requests_total{{method="{method}",status_code="{status}"}} {count}'
                for (method, status), count in sorted(self._requests.items())
            )
            lines += ["# HELP sentinel_dna_investigations_total Completed investigation service calls.", "# TYPE sentinel_dna_investigations_total counter"]
            lines += [f'sentinel_dna_investigations_total{{status="{status}"}} {count}' for status, count in sorted(self._investigations.items())]
            lines += ["# HELP sentinel_dna_investigation_duration_milliseconds_total Aggregate investigation duration.", "# TYPE sentinel_dna_investigation_duration_milliseconds_total counter", f"sentinel_dna_investigation_duration_milliseconds_total {self._investigation_duration_ms}"]
        return "\n".join(lines) + "\n"
