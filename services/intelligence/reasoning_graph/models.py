from dataclasses import asdict,dataclass,field
@dataclass
class ReasoningNode:
 node_id:str; node_type:str; entity_reference:str; confidence:float; explanation:str
 def to_dict(self): return asdict(self)
@dataclass
class ReasoningEdge:
 source:str; destination:str; relationship:str; confidence:float
 def to_dict(self): return asdict(self)
@dataclass
class Hypothesis:
 hypothesis_id:str; statement:str; supporting_evidence:list[str]=field(default_factory=list); confidence:float=.0; required_validation:list[str]=field(default_factory=list)
 def to_dict(self): return asdict(self)
@dataclass
class EvidencePriority:
 evidence_id:str; priority:int; score:float; reason:str
 def to_dict(self): return asdict(self)
