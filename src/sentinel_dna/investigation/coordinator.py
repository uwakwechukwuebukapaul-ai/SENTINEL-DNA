from pathlib import Path
from typing import Any

from sentinel_dna.investigation.context import InvestigationContext
from sentinel_dna.investigation.orchestrator import InvestigationOrchestrator
from sentinel_dna.investigation.result import InvestigationResult


class InvestigationCoordinator:
    def __init__(self, data_dir: str | Path = "data", orchestrator: InvestigationOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator or InvestigationOrchestrator(data_dir)

    def investigate(self, case_id: str, alert: dict[str, Any]) -> InvestigationResult:
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("case_id must be a non-empty string")
        if hasattr(alert, "to_investigation_alert"):
            alert = alert.to_investigation_alert()
        if not isinstance(alert, dict) or not alert:
            raise ValueError("alert must be a non-empty dictionary")
        context = InvestigationContext(case_id=case_id.strip(), alert=alert)
        return self.orchestrator.run(context)
