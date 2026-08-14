from .models import Asset
from .repository import AssetRepository
from .classification import AssetClassifier
from .criticality import CriticalityEngine
from .exposure import ExposureEngine
class AssetService:
 def __init__(self,repository=None): self.repository=repository or AssetRepository(); self.classifier=AssetClassifier(); self.criticality=CriticalityEngine(); self.exposure=ExposureEngine()
 def register_asset(self,**kwargs):
  kwargs["asset_type"]=self.classifier.normalize_asset_type(kwargs.get("asset_type") or self.classifier.classify_asset(kwargs.get("hostname",""),kwargs.get("metadata"))); kwargs["criticality"]=self.criticality.calculate(kwargs["asset_type"],kwargs.get("environment","unknown"),kwargs.get("department","")); return self.repository.create_asset(Asset(**kwargs))
 def get_asset_profile(self,asset_id,tenant_id=None):
  a=self.repository.get_asset(asset_id,tenant_id); return self.calculate_asset_risk(a) if a else None
 def calculate_asset_risk(self,asset,**kwargs): return __import__("services.assets.risk_adapter",fromlist=["adapt_asset_risk"]).adapt_asset_risk(asset,self.exposure.calculate(**kwargs))
 def list_critical_assets(self,tenant_id=None): return [a for a in self.repository.list_assets(tenant_id) if a.criticality=="critical"]
 def get_attack_surface_summary(self,tenant_id=None):
  assets=self.repository.list_assets(tenant_id); return {"total_assets":len(assets),"critical_assets":sum(a.criticality=="critical" for a in assets),"exposed_assets":0,"high_risk_assets":sum(a.criticality in {"critical","high"} for a in assets),"unknown_assets":sum(a.status=="unknown" for a in assets)}
