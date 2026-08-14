from dataclasses import asdict,dataclass,field
@dataclass
class ThreatActor:
 actor_id:str; name:str; aliases:list[str]=field(default_factory=list); techniques:list[str]=field(default_factory=list); targets:list[str]=field(default_factory=list); confidence:float=0.
 def to_dict(self): return asdict(self)
@dataclass
class ThreatCampaign:
 campaign_id:str; name:str; actor:str; indicators:list[str]=field(default_factory=list); techniques:list[str]=field(default_factory=list); timeline:list[str]=field(default_factory=list)
 def to_dict(self): return asdict(self)
