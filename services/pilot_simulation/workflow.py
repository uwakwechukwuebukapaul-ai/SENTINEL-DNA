"""Thin pilot workflow facade over the canonical investigation coordinator."""
from __future__ import annotations
from dataclasses import dataclass
from time import perf_counter
from uuid import uuid4
from services.observability import ObservabilityService
from .scenarios import get_scenario

@dataclass(frozen=True)
class PilotWorkflowResult:
    run_id: str; scenario_id: str; case_id: str; stages: tuple; view: dict | None; metrics: dict | None; duration_ms: float
    def to_dict(self): return {"run_id": self.run_id, "scenario_id": self.scenario_id, "case_id": self.case_id, "stages": list(self.stages), "view": self.view, "metrics": self.metrics, "duration_ms": self.duration_ms, "synthetic_only": False}

class PilotDemoWorkflow:
    """Expose demo progress while delegating execution to InvestigationCoordinator."""
    def execute(self, *, tenant_id, actor_id, case_id, scenario_id, coordinator, alert=None, artifacts=None):
        scenario = get_scenario(scenario_id)
        if not tenant_id or not actor_id: raise PermissionError("pilot_identity_required")
        started = perf_counter(); stages = [{"name": name, "status": "pending"} for name in scenario.expected_flow]
        stages[0]["status"] = "completed"
        try:
            coordinator.investigate(case_id=case_id, alert=alert or scenario.alert, artifacts=artifacts or [], tenant_id=tenant_id, actor_id=actor_id)
            for item in stages[1:7]: item["status"] = "completed"
            context = type("PilotContext", (), {"tenant_id": tenant_id})()
            view = coordinator.get_investigation_view(case_id, context)
            metrics = coordinator.get_investigation_metrics(case_id, context)
            stages[7]["status"] = "ready"; stages[8]["status"] = "ready"; stages[9]["status"] = "completed" if metrics is not None else "pending"
            return PilotWorkflowResult(f"PILOT-{uuid4().hex}", scenario.scenario_id, case_id, tuple(stages), view, metrics, round((perf_counter() - started) * 1000, 2))
        finally:
            ObservabilityService().event("pilot_demo_workflow_completed", investigation_id=case_id, case_id=case_id, tenant_id=tenant_id, status="completed", duration_ms=round((perf_counter() - started) * 1000, 2))
