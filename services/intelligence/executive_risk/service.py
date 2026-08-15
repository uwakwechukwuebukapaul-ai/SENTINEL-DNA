from uuid import uuid4
from .repository import ExecutiveRiskRepository
from .business_assets import BusinessAssetCatalog
from .risk import ExecutiveRiskEngine
from .impact import BusinessImpactEngine
from .aggregation import ExecutiveRiskAggregator
from .recommendations import ExecutiveRecommendations
from .models import ExecutiveRiskAssessment
class ExecutiveRiskService:
    def __init__(self,repository=None,audit=None): self.repository=repository or ExecutiveRiskRepository(); self.assets=BusinessAssetCatalog(self.repository); self.risk=ExecutiveRiskEngine(); self.impact=BusinessImpactEngine(); self.aggregation=ExecutiveRiskAggregator(); self.recommendations=ExecutiveRecommendations(); self.audit=audit
    def register_asset(self,asset): return self.assets.register(asset)
    def assess_asset(self,tenant_id,asset_id,security_risk=0,exposure=0,threat_confidence=0):
        asset=self.repository.get_asset(asset_id,tenant_id)
        if not asset:return None
        score=self.risk.score(asset,security_risk,exposure,threat_confidence); result=ExecutiveRiskAssessment(str(uuid4()),tenant_id,score,self.risk.level(score),1,self.impact.estimate(asset),threat_confidence); self.repository.save_assessment(result); return result
    def recommendations_for(self,tenant_id,asset_id,**kwargs):
        assessment=self.assess_asset(tenant_id,asset_id,**kwargs); asset=self.repository.get_asset(asset_id,tenant_id); result=self.recommendations.generate(tenant_id,asset,assessment.overall_risk) if assessment else []
        for x in result:self.repository.save_finding(x)
        return result
    def summary(self,tenant_id): return self.aggregation.summarize(self.repository.list_assets(tenant_id),self.repository.list_findings(tenant_id))
