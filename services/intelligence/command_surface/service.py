from .models import CommandSnapshot
from .aggregator import CommandAggregator
from .attention import AttentionEvaluator
from .decisions import DecisionBuilder
from .repository import CommandSurfaceRepository
from .evidence import EvidenceContext

class CommandSurfaceService:
    def __init__(self, repository=None, audit=None): self.repository=repository or CommandSurfaceRepository(); self.audit=audit
    def _audit(self, event, tenant_id):
        if self.audit and hasattr(self.audit, "record"): self.audit.record(event, tenant_id=tenant_id)
    def build_snapshot(self, tenant_id, sources=None):
        data=CommandAggregator().aggregate(tenant_id, sources); snap=CommandSnapshot(**data)
        records=list((sources or {}).get("attention", [])); decisions=list((sources or {}).get("decisions", []))
        snap.attention_items=self.build_attention_queue(tenant_id, records); snap.decision_items=self.build_decision_surface(tenant_id, decisions)
        snap.executive_summary=dict((sources or {}).get("executive_summary", {})); self.repository.save_snapshot(snap); self._audit("snapshot", tenant_id); return snap
    def build_attention_queue(self, tenant_id, records=None):
        xs=AttentionEvaluator().build(tenant_id, [x for x in records or [] if x.get("tenant_id", tenant_id)==tenant_id]); self.repository.save_attention(tenant_id,xs); self._audit("attention",tenant_id); return xs
    def build_decision_surface(self, tenant_id, records=None):
        xs=DecisionBuilder().build(tenant_id, [x for x in records or [] if x.get("tenant_id", tenant_id)==tenant_id]); self.repository.save_decisions(tenant_id,xs); self._audit("decisions",tenant_id); return xs
    def get_current_snapshot(self, tenant_id): return self.repository.get_snapshot(tenant_id)
    def get_historical_snapshot(self, tenant_id): self._audit("history",tenant_id); return self.repository.get_history(tenant_id)
    def get_attention_items(self, tenant_id): return self.repository.get_attention(tenant_id)
    def get_decision_items(self, tenant_id): return self.repository.get_decisions(tenant_id)
    def get_subsystem_status(self, tenant_id):
        x=self.get_current_snapshot(tenant_id); return {} if not x else dict(x.subsystem_availability)
    def normalize_evidence(self, item): return EvidenceContext().normalize(item)
