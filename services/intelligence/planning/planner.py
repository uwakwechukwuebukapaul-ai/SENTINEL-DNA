from __future__ import annotations

from typing import Any

from .models import InvestigationPlan
from .rules import PLANNING_RULES


class InvestigationPlanner:
    """Deterministic planning adapter; it never executes tasks."""

    synthetic_only = True

    def __init__(self):
        self._history = []

    def plan(
        self,
        case_id: str,
        security_event: Any = None,
        enrichment: Any = None,
        context: Any = None,
    ) -> InvestigationPlan:

        event = (
            security_event.public()
            if hasattr(security_event, "public")
            else (security_event or {})
        )

        description = str(
            event.get("raw_event", event.get("description", ""))
        ).lower()

        kind = str(
            event.get("event_type", event.get("type", ""))
        ).lower()

        severity = str(
            event.get("severity", "")
        ).lower()

        tags = getattr(enrichment, "tags", []) if enrichment is not None else []

        joined = " ".join(
            [
                description,
                kind,
                severity,
                " ".join(tags),
            ]
        ).lower()

        scenario = (
            "phishing"
            if "phish" in joined
            else "brute_force"
            if "brute" in joined or "authentication" in joined
            else "malware"
            if "malware" in joined
            else "suspicious_communication"
            if "communicat" in joined or "network" in joined
            else "brute_force"
        )

        objective, tasks, priority = PLANNING_RULES[scenario]

        confidence = 0.9 if enrichment is not None else 0.7

        return InvestigationPlan(
            case_id,
            objective,
            tasks,
            priority,
            confidence,
        )

    def create_plan(self, payload: Any) -> dict:
        """
        Legacy compatibility wrapper.
        """

        if not isinstance(payload, dict):
            payload = {}

        case_id = payload.get("case_id", "UNKNOWN")

        plan = self.plan(
            case_id=case_id,
            security_event=payload.get("security_event", payload),
            enrichment=payload.get("enrichment"),
            context=payload.get("context"),
        )

        steps = list(plan.tasks)

        if payload.get("severity", "").lower() in {
            "critical",
            "high",
        }:
            steps.append("map MITRE techniques")

        result = {
            "case_id": plan.case_id,
            "objective": plan.objective,
            "tasks": plan.tasks,
            "steps": steps,
            "priority": plan.priority,
            "confidence": plan.confidence,
            "status": "planned",
        }

        self._history.append(result)

        return result

    def get_history(self):
        """
        Legacy history compatibility.
        """
        return self._history

    def clear_history(self):
        """
        Clears planner history.
        """
        self._history.clear()