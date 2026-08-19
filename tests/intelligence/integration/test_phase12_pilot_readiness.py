"""Phase 12 enterprise pilot scenario and reporting tests."""
from services.pilot_simulation.scenarios import PILOT_SCENARIOS, get_scenario
from services.pilot_simulation.workflow import PilotDemoWorkflow
from services.pilot_reports.service import PilotReportService
from services.pilot_simulation.validation import PilotValidationService
from services.pilot_simulation.service import PilotSimulationService

def test_pilot_catalog_contains_modular_soc_scenarios():
    assert {"phishing_compromise", "suspicious_authentication", "malware_execution", "credential_theft", "cloud_account_compromise"}.issubset(PILOT_SCENARIOS)
    assert all(len(item.expected_flow) == 10 and item.evidence_requirements and item.review_points for item in PILOT_SCENARIOS.values())
    assert all(item.investigation_objectives and item.mitre_techniques and item.expected_outcome for item in PILOT_SCENARIOS.values())

def test_pilot_workflow_delegates_to_canonical_coordinator():
    class Coordinator:
        def __init__(self): self.calls = []
        def investigate(self, **kwargs): self.calls.append(kwargs); return object()
        def get_investigation_view(self, case_id, context): return {"investigation": {"id": "INV-1", "case_id": case_id}, "summary": {}, "feedback": []}
        def get_investigation_metrics(self, case_id, context): return {"feedback_count": 0}
    coordinator = Coordinator()
    result = PilotDemoWorkflow().execute(tenant_id="tenant-a", actor_id="actor-a", case_id="CASE-12", scenario_id="phishing_compromise", coordinator=coordinator)
    assert len(coordinator.calls) == 1
    assert result.to_dict()["stages"][-1]["status"] == "completed"

def test_customer_summary_preserves_evidence_backed_projection():
    view = {"investigation": {"id": "INV-1", "case_id": "CASE-1", "status": "reviewed"}, "summary": {"risk": 0.8, "confidence": 0.7}, "evidence": [{"evidence_id": "E-1"}], "findings": [{"finding_id": "F-1"}], "mitre": [{"technique_id": "T1059"}], "timeline": [], "feedback": [{"decision": "accepted"}], "quality": {"overall_score": 0.9}}
    report = PilotReportService().investigation_summary("tenant-a", view, {"feedback_count": 1})
    assert report["evidence_backed"] is True
    assert report["evidence_analyzed"] == [{"evidence_id": "E-1"}]
    assert report["investigation_metrics"]["feedback_count"] == 1

def test_unknown_scenario_fails_closed():
    try: get_scenario("not-a-scenario")
    except ValueError as exc: assert str(exc) == "unknown_pilot_scenario"
    else: raise AssertionError("unknown scenario accepted")

def test_validation_metrics_measure_product_usefulness_not_analysts():
    run = {"run_id": "RUN-1", "scenario_id": "phishing_compromise", "case_id": "CASE-1", "duration_ms": 120.0, "stages": [{"name": "alert_intake"}], "view": {"summary": {"confidence": .8}, "evidence": [{"id": "1"}, {"id": "2"}], "findings": [{"id": "F-1"}], "feedback": [{"decision": "accepted"}]}, "metrics": {"acceptance_rate": 1.0, "modification_rate": 0.0, "escalation_rate": 0.0}}
    report = PilotValidationService().evaluate(run, ["Evidence was useful."])
    assert report["investigation_completion_time_ms"] == 120.0
    assert report["evidence_coverage"] == 0.666667
    assert report["analyst_scoring"] is False
    assert report["analyst_observations"] == ["Evidence was useful."]

def test_validation_run_lookup_is_tenant_scoped():
    service = PilotSimulationService()
    service.runs.append({"run_id": "RUN-1", "scenario_id": "phishing_compromise", "view": {"investigation": {"tenant_id": "tenant-a"}}})
    try: service.validation_report("tenant-b", "RUN-1")
    except LookupError as exc: assert str(exc) == "pilot_run_not_found"
    else: raise AssertionError("cross-tenant pilot validation was exposed")

def test_pilot_run_lifecycle_and_observations_are_product_scoped():
    service = PilotSimulationService()
    run = service.create_run("tenant-a", "phishing_compromise", "CASE-14")
    assert run["status"] == "created"
    updated = service.record_observation("tenant-a", run["run_id"], {"evidence_usefulness": "Useful supporting references.", "comment": "Clear workflow."})
    assert updated["observations"][0]["evidence_usefulness"] == "Useful supporting references."
    try: service.record_observation("tenant-b", run["run_id"], {"comment": "forged"})
    except LookupError: pass
    else: raise AssertionError("cross-tenant observation was accepted")

def test_pilot_outcome_aggregates_product_metrics_without_analyst_scoring():
    outcome = PilotReportService().pilot_outcome("tenant-a", [{"scenario_id": "phishing_compromise", "status": "completed"}], [{"evidence_count": 2, "findings_generated": 1, "analyst_feedback_count": 1, "acceptance_rate": 1.0, "modification_rate": 0.0, "escalation_rate": 0.0, "confidence_rating": .8, "analyst_observations": ["Clear evidence."], "improvement_opportunities": []}])
    assert outcome["executive_summary"]["investigations_completed"] == 1
    assert outcome["validation_results"]["acceptance_rate"] == 1.0
    assert outcome["analyst_scoring"] is False
