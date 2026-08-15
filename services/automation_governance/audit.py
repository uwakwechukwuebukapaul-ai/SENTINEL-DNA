from datetime import datetime, timezone
class AutomationAudit:
    def __init__(self,sink=None): self.events=[]; self.sink=sink
    def record(self,event,**details):
        item={"event":event,"timestamp":datetime.now(timezone.utc).isoformat(),**details}; self.events.append(item)
        if self.sink and hasattr(self.sink,"record"): self.sink.record(event,**details)
        return item
