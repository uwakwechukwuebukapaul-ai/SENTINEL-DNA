from __future__ import annotations
from datetime import datetime, timezone
from .models import DetectionEvaluation
from .rules import STARTER_RULES
class DetectionEvaluator:
    def __init__(self,rules=None): self.rules=list(rules or STARTER_RULES)
    def evaluate_event(self,event):
        text=str(event).lower(); matched=[]; scores=[]; severities={"low":0,"medium":1,"high":2,"critical":3}
        for rule in self.rules:
            terms=rule.rule_logic.get("terms",[])
            if rule.status=="active" and any(term in text for term in terms): matched.append(rule.id); scores.append(rule.confidence)
        highest=max((r.severity for r in self.rules if r.id in matched),key=lambda x:severities[x],default="low")
        return DetectionEvaluation(str(event.get("event_id") or event.get("id") or "event-0") if isinstance(event,dict) else "event-0",matched,len(matched),highest,round(sum(scores)/len(scores),4) if scores else 0.0,True)
    def evaluate_batch(self,events): return [self.evaluate_event(event) for event in events]
