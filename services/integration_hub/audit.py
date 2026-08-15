from datetime import datetime, timezone
class IntegrationHubAudit:
    def __init__(self, sink=None): self.sink, self.events = sink, []
    def record(self, event, **details):
        item = {"event": event, "timestamp": datetime.now(timezone.utc).isoformat(), **details}; self.events.append(item)
        if self.sink and hasattr(self.sink, "record"): self.sink.record(event, **details)
        return item
