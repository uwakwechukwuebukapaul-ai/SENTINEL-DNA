"""Secret-free evidence serialization for the disposable harness."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Mapping


_SECRET_NAME = re.compile(
    r"(secret|password|passwd|token|credential|access.?key|private.?key|session)",
    re.IGNORECASE,
)


def _safe(value: Any, key: str = "") -> Any:
    if _SECRET_NAME.search(key):
        raise ValueError(f"sensitive evidence field refused: {key}")
    if isinstance(value, Mapping):
        return {str(k): _safe(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(item, key) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"unsupported evidence value: {type(value).__name__}")


def sanitize(record: Mapping[str, Any]) -> dict[str, Any]:
    return _safe(record)


def canonical_evidence(record: Mapping[str, Any]) -> bytes:
    return json.dumps(sanitize(record), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def new_evidence(run_id: str, account_id: str, region: str) -> dict[str, Any]:
    return {
        "schema": "sentinel-dna-b3-disposable-integration-v1",
        "run_id": run_id,
        "account_id": account_id,
        "region": region,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "cleanup": {"status": "PENDING", "resources": []},
        "tests": [],
    }

