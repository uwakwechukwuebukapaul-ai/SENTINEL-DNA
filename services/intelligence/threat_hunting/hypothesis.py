from uuid import uuid4
from .models import ThreatHypothesis

class HypothesisEngine:
    def create(self, tenant_id, threat_intelligence=None, attack_paths=None, detection_gaps=None, behavior_anomalies=None):
        signals=[str(x) for x in (threat_intelligence or []) + (attack_paths or []) + (detection_gaps or []) + (behavior_anomalies or [])]
        title="Investigate suspicious behavior" if signals else "Baseline behavior review"
        techniques=[item for item in signals if item.startswith("T") and item[1:5].isdigit()]
        return ThreatHypothesis(str(uuid4()), tenant_id, title, "Generated from available threat, path, detection, and behavior intelligence", sorted(set(techniques)), min(0.95, .5 + .1 * len(signals)))
