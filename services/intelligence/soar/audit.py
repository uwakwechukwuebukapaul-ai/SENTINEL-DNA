from datetime import datetime, timezone
class SOARAuditLogger:
    def __init__(self): self.events=[]
    def record(self,event,**data): self.events.append({"event":event,"timestamp":datetime.now(timezone.utc).isoformat(),**data}); return self.events[-1]
