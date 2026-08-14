from datetime import datetime, timezone
from typing import Any

def serialize(value):
    if value is None: return None
    if hasattr(value, "to_dict"): return value.to_dict()
    return value

class SOCResponse:
    def __init__(self, success=True, data=None, warnings=None, error=None): self.success,self.data,self.warnings,self.error=success,data,warnings or [],error
    def to_dict(self):
        d={"success":self.success,"data":serialize(self.data),"warnings":self.warnings,"timestamp":datetime.now(timezone.utc).isoformat()}
        if self.error: d["error"]=self.error
        return d
