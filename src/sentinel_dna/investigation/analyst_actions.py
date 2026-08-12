"""Analyst-controlled case actions with durable audit records."""
from typing import Any
from sentinel_dna.case_management.case_store import CaseStore


class AnalystActionService:
    """Records human decisions; it never performs automated containment."""
    ALLOWED_ACTIONS = {"confirm_finding", "dismiss_finding", "escalate", "add_note"}

    def __init__(self, data_dir: str = "data") -> None:
        self.case_store = CaseStore(data_dir)

    def record(self, case_id: str, action: str, analyst: str, note: str = "",
               metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if action not in self.ALLOWED_ACTIONS:
            raise ValueError(f"Unsupported analyst action: {action}")
        if not analyst.strip():
            raise ValueError("analyst must be a non-empty string")
        if action == "add_note" and not note.strip():
            raise ValueError("note is required when adding an analyst note")
        case = self.case_store.get(case_id)
        if action == "escalate":
            case.status = "escalated"
        elif action == "dismiss_finding":
            case.status = "reviewed"
        event = {"action": action, "analyst": analyst.strip(), "note": note.strip(), **(metadata or {})}
        case.add_event("analyst_action", f"Analyst {action.replace('_', ' ')}", event)
        self.case_store.save(case)
        return {"case_id": case_id, "status": case.status, "audit_event": event}
