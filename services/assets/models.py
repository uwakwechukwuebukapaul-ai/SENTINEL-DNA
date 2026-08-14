from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from typing import Any
@dataclass
class Asset:
 asset_id:str; tenant_id:str; hostname:str; asset_type:str="unknown"; owner:str=""; department:str=""; environment:str="unknown"; criticality:str="medium"; status:str="active"; metadata:dict[str,Any]=field(default_factory=dict); created_at:str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat())
 def to_dict(self): return asdict(self)
@dataclass
class AssetRiskProfile:
 asset_id:str; risk_score:int; business_impact:str; exposure_level:str; threat_level:str; recommendations:list[str]=field(default_factory=list)
 def to_dict(self): return asdict(self)
@dataclass
class AssetRelationship:
 source_asset:str; target_asset:str; relationship_type:str
 def to_dict(self): return asdict(self)
