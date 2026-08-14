from dataclasses import asdict,dataclass,field
@dataclass
class BehaviorPattern:
 pattern_id:str; name:str; behavior_type:str; indicators:list[str]=field(default_factory=list); confidence:float=0.; mitre_techniques:list[str]=field(default_factory=list)
 def to_dict(self): return asdict(self)
@dataclass
class DetectionCandidate:
 candidate_id:str; name:str; description:str; evidence_refs:list[str]=field(default_factory=list); mitre_techniques:list[str]=field(default_factory=list); confidence:float=0.; recommendation_type:str="new_detection"
 def to_dict(self): return asdict(self)
