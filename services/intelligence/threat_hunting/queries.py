from uuid import uuid4
from .models import HuntingQuery, ThreatHypothesis

def generate_queries(hypothesis: ThreatHypothesis):
    return [HuntingQuery(str(uuid4()), hypothesis.tenant_id, kind, f"hunt {kind} for {hypothesis.title}", hypothesis.mitre_techniques) for kind in ("identity", "endpoint", "network", "ioc")]
