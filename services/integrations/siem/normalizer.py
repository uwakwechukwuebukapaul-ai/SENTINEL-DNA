from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from .schemas import SecurityEvent, event_id

def normalize_event(vendor_event: dict[str, Any] | None, source: str = "generic") -> SecurityEvent:
    raw = dict(vendor_event or {})
    timestamp = raw.get("timestamp") or raw.get("time") or datetime.now(timezone.utc).isoformat()
    severity = str(raw.get("severity") or raw.get("level") or "unknown").lower()
    entities = raw.get("entities") or []
    if not isinstance(entities, list):
        entities = [{"value": entities}]
    return SecurityEvent(event_id(raw.get("event_id") or raw.get("id")), source, str(timestamp), severity, entities, raw)
