from dataclasses import asdict,dataclass,field
@dataclass
class ExposureAssessment:
 exposure_score:int; exposure_level:str; contributing_factors:list[str]=field(default_factory=list); recommendations:list[str]=field(default_factory=list)
 def to_dict(self): return asdict(self)
class ExposureAnalyzer:
 def calculate(self,asset_criticality="medium",vulnerability_severity="medium",exploit_available=False,threat_activity=0,privilege_level="user",external_exposure=False):
  score=min(100,(30 if asset_criticality=="critical" else 20 if asset_criticality=="high" else 10)+({"critical":30,"high":20,"medium":10,"low":3}.get(vulnerability_severity,3))+int(exploit_available)*15+threat_activity*10+(15 if privilege_level=="admin" else 0)+int(external_exposure)*20); return ExposureAssessment(score,"high" if score>70 else "medium" if score>30 else "low",[],["Prioritize path review"] if score>70 else [])
