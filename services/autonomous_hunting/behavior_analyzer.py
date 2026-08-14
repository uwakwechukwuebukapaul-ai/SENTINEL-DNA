from .models import HuntFinding
class BehaviorAnalyzer:
 def analyze(self,org,hunt_id,events):
  return [HuntFinding(org,hunt_id,"HIGH",getattr(e,"entity",getattr(e,"user_id","unknown")),"ENTITY","Suspicious behavior identified",[e.public()] if hasattr(e,"public") else [e],(e.metadata.get("mitre","T1003") if hasattr(e,"metadata") else "T1003"),.85) for e in events]
