"""Read-only enterprise pilot validation metrics over canonical projections."""
from __future__ import annotations
from .scenarios import get_scenario

class PilotValidationService:
    """Evaluate Sentinel DNA usefulness; never score analysts or mutate evidence."""
    def evaluate(self, run, analyst_observations=None):
        run = dict(run or {}); scenario = get_scenario(run.get("scenario_id"))
        view = dict(run.get("view") or {}); summary = dict(view.get("summary") or {}); metrics = dict(run.get("metrics") or {})
        evidence = list(view.get("evidence") or []); findings = list(view.get("findings") or []); feedback = list(view.get("feedback") or [])
        required = len(scenario.evidence_requirements)
        evidence_coverage = round(min(len(evidence) / required, 1.0), 6) if required else 0.0
        decisions = [str(item.get("decision", "")).lower() for item in feedback if isinstance(item, dict)]
        return {"run_id": run.get("run_id"), "scenario_id": scenario.scenario_id, "case_id": run.get("case_id"), "validation_lifecycle": [item.get("name") for item in run.get("stages", [])], "investigation_completion_time_ms": float(run.get("duration_ms") or 0), "evidence_coverage": evidence_coverage, "evidence_count": len(evidence), "findings_generated": len(findings), "analyst_feedback_count": len(feedback), "acceptance_rate": metrics.get("acceptance_rate", 0.0), "modification_rate": metrics.get("modification_rate", 0.0), "escalation_rate": metrics.get("escalation_rate", 0.0), "confidence_rating": summary.get("confidence", 0), "mitre_mapping_quality": 1.0 if view.get("mitre") else 0.0, "finding_usefulness": 1.0 if findings else 0.0, "accepted_recommendations": decisions.count("accepted"), "modified_recommendations": decisions.count("modified"), "escalation_decisions": decisions.count("escalated"), "advisory_findings": len(findings), "analyst_observations": [str(item) for item in (analyst_observations or []) if item], "improvement_opportunities": self._opportunities(evidence_coverage, len(feedback), findings), "advisory_only": True, "analyst_scoring": False}
    @staticmethod
    def _opportunities(evidence_coverage, feedback_count, findings):
        values = []
        if evidence_coverage < 1: values.append("Collect the scenario's expected evidence before relying on the investigation.")
        if not findings: values.append("Review evidence coverage because no AI findings were generated.")
        if not feedback_count: values.append("Collect an analyst outcome before evaluating recommendation usefulness.")
        return values
