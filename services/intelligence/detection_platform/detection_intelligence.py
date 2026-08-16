from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class DetectionIntelligence:
 tenant_id:str; intelligence_id:str; posture:str="insufficient_data"; observed_rule_count:int=0; derived_maturity:str="insufficient_data"; coverage_confidence:str="insufficient_data"; evidence_references:tuple=(); uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
 def to_dict(self):return asdict(self)
