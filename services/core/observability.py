"""Small, dependency-free observability primitives for request boundaries."""
from __future__ import annotations

import re
from uuid import uuid4


_CORRELATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


def normalize_correlation_id(value: object | None) -> str:
    """Return a safe bounded correlation identifier or generate one.

    Correlation identifiers are diagnostic metadata, never an authorization
    input. Rejecting control characters and oversized values prevents request
    headers from becoming response-header or log injection vectors.
    """
    candidate = str(value or "").strip()
    if _CORRELATION_ID.fullmatch(candidate):
        return candidate
    return str(uuid4())


def request_metric_bucket(app) -> dict[str, int]:
    """Return the process-local request counters used by health diagnostics."""
    bucket = app.extensions.setdefault(
        "sentinel_request_metrics",
        {"requests": 0, "errors": 0, "api_requests": 0},
    )
    return bucket


__all__ = ["normalize_correlation_id", "request_metric_bucket"]
