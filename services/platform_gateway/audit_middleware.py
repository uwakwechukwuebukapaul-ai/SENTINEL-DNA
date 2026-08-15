from datetime import datetime, timezone
class GatewayAuditLogger:
    def __init__(self, sink=None): self.sink, self.events = sink, []
    def record(self, event_type, *, context=None, tenant_id=None, **details):
        event = {"event_type": event_type, "tenant_id": tenant_id or getattr(context, "tenant_id", None), "request_id": getattr(context, "request_id", None), "timestamp": datetime.now(timezone.utc).isoformat(), "details": details}
        self.events.append(event)
        if self.sink and hasattr(self.sink, "record"):
            try: self.sink.record(event_type, details=event)
            except TypeError: self.sink.record(event_type, **details)
        return event
