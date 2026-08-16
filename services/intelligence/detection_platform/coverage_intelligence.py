from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class CoverageIntelligence:
 tenant_id:str; coverage_id:str; attack_coverage_posture:str="insufficient_data"; telemetry_coverage_posture:str="insufficient_data"; detection_maturity_indicators:tuple=(); blind_spot_observations:tuple=(); confidence:str="insufficient_data"; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
 def to_dict(self):return asdict(self)
