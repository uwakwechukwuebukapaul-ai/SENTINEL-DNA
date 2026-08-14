from datetime import datetime, timezone
from .models import NormalizedSecurityEvent, SecurityEvent

class SecurityEventNormalizer:
    CATEGORIES = {"identity": "identity", "login": "identity", "authentication": "identity", "network": "network", "dns": "network", "firewall": "network", "endpoint": "endpoint", "process": "endpoint", "file": "endpoint", "cloud": "cloud", "iam": "cloud"}
    def normalize(self, event: SecurityEvent) -> NormalizedSecurityEvent:
        event_type = event.event_type.lower(); category = self.CATEGORIES.get(event_type, next((value for key, value in self.CATEGORIES.items() if key in event_type), "endpoint"))
        timestamp = str(event.payload.get("timestamp") or event.payload.get("time") or event.received_at or datetime.now(timezone.utc).isoformat())
        return NormalizedSecurityEvent(event.event_id, event.tenant_id, category, event.event_type, timestamp, event.source, dict(event.payload), event.event_id)
