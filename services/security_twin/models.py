from dataclasses import asdict,dataclass,field
from uuid import uuid4
@dataclass
class SecurityAsset:
 organization_id:str; type:str; name:str; criticality:str="MEDIUM"; owner:str=""; risk_level:str="MEDIUM"; metadata:dict=field(default_factory=dict); id:str=field(default_factory=lambda:str(uuid4()))
 def public(self): return asdict(self)
@dataclass
class AssetRelationship:
 organization_id:str; source_asset:str; target_asset:str; relationship_type:str; confidence:float=.8; id:str=field(default_factory=lambda:str(uuid4()))
 def public(self): return asdict(self)
@dataclass
class AttackPath:
 organization_id:str; source:str; target:str; steps:list=field(default_factory=list); mitre_mapping:list=field(default_factory=list); risk_score:float=0
 def public(self): return asdict(self)
