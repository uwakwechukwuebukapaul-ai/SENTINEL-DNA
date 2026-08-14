from __future__ import annotations
from typing import Any
from .models import InvestigationPlan
from .rules import PLANNING_RULES

class InvestigationPlanner:
    """Deterministic planning adapter; it never executes tasks."""
    synthetic_only = True

    def plan(self, case_id: str, security_event: Any = None, enrichment: Any = None, context: Any = None) -> InvestigationPlan:
        event = security_event.public() if hasattr(security_event, "public") else (security_event or {})
        description = str(event.get("raw_event", event.get("description", ""))).lower()
        kind = str(event.get("event_type", event.get("type", ""))).lower()
        tags = getattr(enrichment, "tags", []) if enrichment is not None else []
        joined = " ".join([description, kind, " ".join(tags)]).lower()
        scenario = "phishing" if "phish" in joined else "brute_force" if "brute" in joined or "authentication" in joined else "malware" if "malware" in joined else "suspicious_communication" if "communicat" in joined or "network" in joined else "brute_force"
        objective, tasks, priority = PLANNING_RULES[scenario]
        confidence = 0.9 if enrichment is not None else 0.7
        return InvestigationPlan(case_id, objective, tasks, priority, confidence)
