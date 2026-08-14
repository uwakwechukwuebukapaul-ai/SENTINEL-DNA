from datetime import datetime, timezone
from .models import NormalizedEvent
class EventNormalizer:
    def normalize(self, event, source="generic"):
        event = event or {}; timestamp = event.get("timestamp") or datetime.now(timezone.utc).isoformat()
        return NormalizedEvent(timestamp, source, str(event.get("hostname", "unknown")), str(event.get("user", "unknown")), str(event.get("event_type", event.get("type", "unknown"))), str(event.get("severity", "info")).lower(), event)
