from .path_engine import AttackPathEngine
from .analyzer import AttackPathAnalyzer
from .blast_radius import BlastRadiusAnalyzer
class AttackPathService:
 def __init__(self,repository): self.engine=AttackPathEngine(repository); self.analyzer=AttackPathAnalyzer(repository); self.blast=BlastRadiusAnalyzer(repository)
 def analyze_paths(self,start,tenant_id=None): return [self.analyzer.analyze(tenant_id,p) for p in self.engine.identify_high_risk_paths(start,tenant_id)]
 def get_blast_radius(self,entity,tenant_id=None): return self.blast.analyze(entity,tenant_id)
