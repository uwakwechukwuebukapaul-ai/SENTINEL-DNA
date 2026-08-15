from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class AnalystWorkspaceContext:
    tenant_id:str; case:dict=field(default_factory=dict); investigation:dict=field(default_factory=dict); evidence:list=field(default_factory=list); threat:list=field(default_factory=list); timeline:list=field(default_factory=list); risk:dict=field(default_factory=dict); compliance:dict=field(default_factory=dict); fabric:dict=field(default_factory=dict); copilot:dict=field(default_factory=dict); decisions:list=field(default_factory=list); quality:dict=field(default_factory=dict); optimization:dict=field(default_factory=dict); availability:dict=field(default_factory=dict); state:str="ready"; generated_at:str=field(default_factory=now)
    def to_dict(self): return asdict(self)
class WorkspaceContextBuilder:
    def build(self,tenant_id,record=None,**sources):
        data=record.to_dict() if hasattr(record,"to_dict") else dict(record or {}); availability={}; values={}
        for name in ("evidence","threat","timeline","risk","compliance","fabric","copilot","decisions","quality","optimization"):
            value=sources.get(name,data.get(name,data.get(f"{name}_context",data.get(f"{name}_summary"))))
            availability[name]={"available":value is not None,"status":"available" if value is not None else "unavailable"}; values[name]=value if value is not None else ([] if name in {"evidence","threat","timeline","decisions"} else {})
        values["case"]=sources.get("case",{"case_id":data.get("case_id"),"title":data.get("title"),"status":data.get("status"),"severity":data.get("severity")}); values["investigation"]={k:data.get(k) for k in ("investigation_id","status","plan","findings","confidence","recommendations") if data.get(k) is not None}
        state="ready" if all(x["available"] for x in availability.values()) else "partial"; return AnalystWorkspaceContext(tenant_id,availability=availability,state=state,**values)
