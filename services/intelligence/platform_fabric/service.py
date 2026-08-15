from .adapters import *
from .aggregator import PlatformAggregator
from .prioritizer import PlatformPrioritizer
from .provenance import ProvenanceIndex
from .relationships import RelationshipBuilder
from .repository import PlatformFabricRepository
class PlatformIntelligenceService:
    def __init__(self,repository=None,audit=None,adapters=None): self.repository=repository or PlatformFabricRepository(); self.audit=audit; self.adapters=adapters or {}; self.aggregator=PlatformAggregator(); self.prioritizer=PlatformPrioritizer(); self.provenance=ProvenanceIndex(); self.relationships=RelationshipBuilder()
    def _audit(self,event,**data):
        if self.audit and hasattr(self.audit,"record"): self.audit.record(event,**data)
    def aggregate(self,tenant_id,sources):
        records=[]; availability={}
        for name,items in (sources or {}).items():
            adapter=self.adapters.get(name) or {"investigation":InvestigationAdapter,"threat_intelligence":ThreatAdapter,"evidence":EvidenceAdapter,"incident_management":IncidentAdapter,"exposure_management":ExposureAdapter,"security_posture":PostureAdapter,"compliance":ComplianceAdapter,"governance_decision":GovernanceAdapter,"operations":OperationsAdapter,"executive_risk":ExecutiveRiskAdapter,"command_center":CommandCenterAdapter}.get(name,IntelligenceAdapter)();
            try: records.extend(adapter.normalize(tenant_id,items)); availability[name]={"available":True,"count":len(items or [])}
            except Exception as exc: availability[name]={"available":False,"reason":str(exc)}
        relationships=self.relationships.build(tenant_id,records); snapshot=self.aggregator.build(tenant_id,records,relationships,availability,self.prioritizer,self.provenance); self.repository.save_records(records); self.repository.save_relationships(relationships); self.repository.save_attention(snapshot.attention_queue); self._audit("platform_intelligence_aggregated",tenant_id=tenant_id); return snapshot
    def build_snapshot(self,tenant_id,sources):
        snapshot=self.aggregate(tenant_id,sources); self.repository.save_snapshot(snapshot); self._audit("platform_snapshot_generated",tenant_id=tenant_id); return snapshot
    def unified_intelligence(self,tenant_id): return self.repository.list_records(tenant_id)
    def cross_domain_relationships(self,tenant_id): return self.repository.list_relationships(tenant_id)
    def attention_queue(self,tenant_id): return self.repository.list_attention(tenant_id)
    def historical_snapshots(self,tenant_id): self._audit("platform_historical_retrieved",tenant_id=tenant_id); return self.repository.list_snapshots(tenant_id)
    def provenance_for(self,tenant_id): return [x.provenance for x in self.repository.list_records(tenant_id)]
