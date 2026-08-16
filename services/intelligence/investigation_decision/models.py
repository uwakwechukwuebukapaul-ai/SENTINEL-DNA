from dataclasses import asdict,dataclass
import hashlib
def stable_id(t,k):return f"{k}-{hashlib.sha256(f'{t}:{k}'.encode()).hexdigest()[:20]}"
@dataclass(frozen=True)
class DecisionAnalysis:
 tenant_id:str;analysis_id:str;decision_posture:str="insufficient_evidence";evidence_confidence:str="insufficient_evidence";uncertainty:tuple=();contributing_factors:tuple=();recommended_investigation_considerations:tuple=();provenance:tuple=();advisory_only:bool=True
 def to_dict(self):return asdict(self)
