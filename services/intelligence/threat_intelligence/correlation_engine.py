from __future__ import annotations
import hashlib, json
from .models import ThreatIndicator, ThreatMatch, ThreatIntelligenceReport
from .repository import ThreatIntelligenceRepository
from .scoring import score_threat

class ThreatCorrelationEngine:
    def __init__(self, repository=None): self.repository = repository or ThreatIntelligenceRepository()
    @staticmethod
    def _data(value):
        if hasattr(value, "snapshot"): return value.snapshot()
        return value.to_dict() if hasattr(value, "to_dict") else (value or {})
    def correlate_case(self, context, evidence=None, iocs=None, memory_references=None):
        data = self._data(context); case_id = str(data.get("case_id", "unknown")); items = list(iocs or data.get("iocs", []) or [])
        matches=[]
        for index, item in enumerate(items):
            if isinstance(item, str): value, kind = item, "domain"
            else: value, kind = str(item.get("value") or item.get("indicator") or ""), str(item.get("type") or item.get("indicator_type") or "domain")
            if not value: continue
            indicator_id = "TI-" + hashlib.sha256(f"{kind}|{value}".encode()).hexdigest()[:16]
            indicator = self.repository.search_indicator(value, kind)
            ind = indicator[0] if indicator else self.repository.add_indicator(ThreatIndicator(indicator_id, kind, value, confidence=.75, tags=["phishing"] if "login" in value or "malicious" in value else []))
            self.repository.link_indicator_to_case(ind.indicator_id, case_id); cases=self.repository.get_related_cases(ind.indicator_id)
            matches.append(ThreatMatch(ind, [c for c in cases if c != case_id], [], .85 if len(cases)>1 else .65, "infrastructure_reuse" if len(cases)>1 else "new_indicator", [str(item.get("id") or item.get("evidence_id") or f"evidence-{index}")] if isinstance(item, dict) else []))
        similarity = min(1.0, sum(bool(m.matched_cases) for m in matches) / max(1, len(matches)))
        scored=score_threat(80 if matches else 0, min(100,len(matches)*20), similarity*100, 80 if matches else 20, 70 if matches else 0)
        return ThreatIntelligenceReport(case_id, matches, scored["score"], similarity, f"Matched {len(matches)} indicators and {sum(bool(m.matched_cases) for m in matches)} reused infrastructure patterns.", ["Review related cases and validate indicator reputation."] if matches else [], True)
