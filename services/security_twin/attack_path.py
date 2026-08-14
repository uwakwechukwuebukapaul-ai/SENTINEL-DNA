from .models import AttackPath
class AttackPathEngine:
 def analyze(self,org,asset_id,relationships): return [AttackPath(org,x.source_asset,x.target_asset,[x.relationship_type],["T1078"],round(100*x.confidence,2)) for x in relationships]
