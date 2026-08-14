from .models import BehaviorAnomaly
class AnomalyDetectionEngine:
    def __init__(self, repository): self.repository=repository
    def detect(self, organization_id, events):
        result=[]
        for e in events:
            d=e.normalized_event or e.raw_event; kind=None; mitre=[]
            if d.get("impossible_travel"): kind="impossible_travel"; mitre=["T1078"]
            elif d.get("rare_process") or d.get("suspicious_powershell"): kind="rare_process_execution"; mitre=["T1059.001"]
            elif d.get("password_spray") or e.event_type.lower() == "password_spray": kind="password_spraying"; mitre=["T1110.003"]
            elif d.get("privilege_change"): kind="privilege_change"; mitre=["T1098"]
            if kind:
                item=BehaviorAnomaly(organization_id,e.user_id or e.asset_id,kind,"Behavior deviates from established baseline",85,0.9,mitre); self.repository.anomalies.append(item); result.append(item)
        return result
