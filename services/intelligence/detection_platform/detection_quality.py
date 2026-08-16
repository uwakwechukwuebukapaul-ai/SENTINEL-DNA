from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class DetectionQuality:
 tenant_id:str; quality_id:str; rule_quality_indicators:tuple=(); validation_status:str="insufficient_data"; metadata_completeness:str="insufficient_data"; coverage_confidence:str="insufficient_data"; stale_rule_indicators:tuple=(); uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
 def to_dict(self):return asdict(self)
