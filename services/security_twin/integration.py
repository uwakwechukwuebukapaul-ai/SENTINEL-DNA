from .models import SecurityAsset
from .asset_graph import AssetGraph
from .relationship_engine import RelationshipEngine
from .attack_path import AttackPathEngine
from .blast_radius import BlastRadiusEngine
from .risk_engine import TwinRiskEngine
class SecurityTwinService:
 def __init__(self,repository): self.repository=repository; self.graph=AssetGraph(repository); self.relationships=RelationshipEngine(); self.paths=AttackPathEngine(); self.blast=BlastRadiusEngine(); self.risk=TwinRiskEngine()
 def add_asset(self,org,data): x=SecurityAsset(org,data.get("type","ASSET"),data.get("name",""),data.get("criticality","MEDIUM"),data.get("owner",""),data.get("risk_level","MEDIUM"),data.get("metadata",{})); self.repository.assets.append(x); return x
 def context(self,org,asset_id):
  assets=self.repository.scoped(self.repository.assets,org); asset=next((x for x in assets if x.id==asset_id),None)
  if not asset:return None
  rel=self.relationships.neighbors(self.repository,org,asset_id); paths=self.paths.analyze(org,asset_id,rel); blast=self.blast.calculate(org,asset_id,assets,self.repository.scoped(self.repository.relationships,org)); return {"asset":asset.public(),"attack_paths":[x.public() for x in paths],"blast_radius":blast,"risk":self.risk.calculate(asset,blast["count"],len(paths)),"business_impact":asset.metadata.get("business_impact","")}
