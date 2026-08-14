from __future__ import annotations
import hashlib, json
from typing import Any
from .models import HuntResult, HuntingQuery

class HuntQueryEngine:
    """Read-only deterministic search over supplied intelligence snapshots."""
    def __init__(self, memory_service=None, threat_repository=None): self.memory_service, self.threat_repository = memory_service, threat_repository
    @staticmethod
    def _data(value):
        if value is None: return {}
        if hasattr(value, "to_dict"): return value.to_dict()
        if hasattr(value, "snapshot"): return value.snapshot()
        return value if isinstance(value, dict) else dict(vars(value))
    def _run(self, query, query_type, context=None, report=None, memory_references=None):
        c, r = self._data(context), self._data(report); q=str(query).lower(); matches=[]; cases=[]; indicators=[]
        haystack=json.dumps({"context":c,"report":r,"memory":memory_references}, default=str).lower()
        if q in haystack:
            matches.append({"query": query, "source": "investigation_intelligence", "case_id": c.get("case_id")})
            if c.get("case_id"): cases.append(str(c["case_id"]))
        for item in (c.get("iocs", []) or []):
            value=str(item.get("value") or item.get("indicator") or "") if isinstance(item,dict) else str(item)
            if value and q in value.lower(): indicators.append(value); matches.append({"indicator": value, "type": item.get("type", "unknown") if isinstance(item,dict) else "unknown"})
        query_id="Q-"+hashlib.sha256(f"{query_type}|{query}".encode()).hexdigest()[:16]
        return HuntResult(query_id,matches,cases,sorted(set(indicators)),.8 if matches else .1,f"Found {len(matches)} match(es) for {query_type} query '{query}'.",True)
    def search_ioc(self, query, context=None, threat_report=None, memory_references=None): return self._run(query,"ioc",context,threat_report,memory_references)
    def search_cases(self, query, context=None, threat_report=None, memory_references=None): return self._run(query,"case",context,threat_report,memory_references)
    def search_mitre(self, query, context=None, threat_report=None, memory_references=None): return self._run(query,"mitre",context,threat_report,memory_references)
    def search_campaigns(self, query, context=None, threat_report=None, memory_references=None): return self._run(query,"campaign",context,threat_report,memory_references)
    def search_behavior(self, query, context=None, threat_report=None, memory_references=None): return self._run(query,"behavior",context,threat_report,memory_references)
