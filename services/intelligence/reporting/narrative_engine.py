"""Deterministic, advisory investigation narrative generation."""
from __future__ import annotations
import hashlib
from typing import Any
from .models import InvestigationNarrative
from .templates import EXECUTIVE_SUMMARY_TEMPLATE, ANALYST_REPORT_TEMPLATE, INCIDENT_STORY_TEMPLATE

class InvestigationNarrativeEngine:
    def __init__(self, ai_runtime: Any = None) -> None: self.ai_runtime = ai_runtime
    @staticmethod
    def _data(value):
        if value is None: return {}
        if hasattr(value, "to_dict"): return dict(value.to_dict())
        if hasattr(value, "snapshot"): return dict(value.snapshot())
        return dict(value) if isinstance(value, dict) else dict(vars(value))
    def _parts(self, context, result, reasoning, decision, copilot, memory):
        c,r,rr,d,cp = map(self._data, (context,result,reasoning,decision,copilot))
        evidence = c.get("evidence", []) or r.get("artifacts", []) or []
        refs = [str(x.get("id") or x.get("evidence_id")) for x in evidence if isinstance(x, dict)]
        what = rr.get("summary") or cp.get("answer") or "No investigation conclusion was recorded."
        actions = r.get("recommendations", []) or d.get("recommended_actions", []) or []
        timeline = c.get("timeline", []) or []
        confidence = float(r.get("confidence") or rr.get("confidence") or 0.0)
        return c,r,rr,d,cp,refs,what,actions,timeline,confidence
    def generate_executive_summary(self, context, result, reasoning_report=None, decision_report=None, copilot_summary=None, memory_reference=None):
        *_, what, actions, timeline, confidence = self._parts(context,result,reasoning_report,decision_report,copilot_summary,memory_reference)
        return EXECUTIVE_SUMMARY_TEMPLATE.format(what_happened=what, why_it_matters="The findings inform SOC triage and response priority", confidence=f"{confidence:.0%}", actions="; ".join(map(str,actions)) or "Analyst review")
    def generate_analyst_summary(self, context, result, reasoning_report=None, decision_report=None, copilot_summary=None, memory_reference=None):
        *_, refs, what, actions, _, confidence = self._parts(context,result,reasoning_report,decision_report,copilot_summary,memory_reference)
        return ANALYST_REPORT_TEMPLATE.format(what_happened=what, evidence=", ".join(refs) or "none recorded", confidence=f"{confidence:.0%}", actions="; ".join(map(str,actions)) or "Analyst review")
    def generate_incident_story(self, context, result, reasoning_report=None, decision_report=None, copilot_summary=None, memory_reference=None):
        c,r,rr,d,cp,refs,what,actions,timeline,confidence = self._parts(context,result,reasoning_report,decision_report,copilot_summary,memory_reference)
        attack = ", ".join(r.get("mitre", []) or rr.get("mitre_techniques", []) or ["no technique mapped"])
        return INCIDENT_STORY_TEMPLATE.format(what_happened=what, timeline=" -> ".join(str(x) for x in timeline) or ", ".join(refs) or "none recorded", attack_analysis=attack)
    def generate_report(self, context, result, reasoning_report=None, decision_report=None, copilot_summary=None, memory_reference=None):
        c,r,rr,d,cp,refs,what,actions,timeline,confidence = self._parts(context,result,reasoning_report,decision_report,copilot_summary,memory_reference)
        case_id = str(c.get("case_id") or r.get("case_id") or "unknown")
        report_id = "NAR-" + hashlib.sha256(f"{case_id}|{what}|{memory_reference or ''}".encode()).hexdigest()[:20]
        return InvestigationNarrative(report_id, case_id, "SOC Investigation Narrative", self.generate_executive_summary(context,result,reasoning_report,decision_report,copilot_summary,memory_reference), self.generate_analyst_summary(context,result,reasoning_report,decision_report,copilot_summary,memory_reference), self.generate_incident_story(context,result,reasoning_report,decision_report,copilot_summary,memory_reference), timeline, ", ".join(r.get("mitre", []) or rr.get("mitre_techniques", [])), d.get("rationale", "Decision rationale unavailable."), list(actions), confidence, True)
