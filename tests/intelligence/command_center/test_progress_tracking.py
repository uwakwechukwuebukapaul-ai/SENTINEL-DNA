from services.intelligence.command_center.progress_tracking import ExecutiveProgressObservation, stable_observation_id
from services.intelligence.command_center.progress_tracking_service import ExecutiveProgressTrackingService

def obs(period, delta, state="improving", tenant="a"):
    return {"tenant_id": tenant, "program_id": "p1", "dimension": "detection", "observation_period": period, "state": state, "score": 50 + (delta or 0), "score_delta": delta, "confidence": .7, "evidence_strength": "moderate"}

def test_stable_ids_and_tenant_isolation():
    a = ExecutiveProgressObservation("a", "p", "d", "2026-01", "improving")
    assert a.stable_id == stable_observation_id("a", "p", "d", "2026-01", None, "improving")
    result = ExecutiveProgressTrackingService().track("a", [obs("2026-01", 1), obs("2026-02", 1), obs("2026-03", 1), obs("2026-04", 1, tenant="b")])
    assert len(result["progress"]) == 1
    assert result["progress"][0]["current_state"] == "sustained_improvement"

def test_persistent_regression_and_transition():
    result = ExecutiveProgressTrackingService().track("a", [obs("2026-01", 1), obs("2026-02", -1, "regression"), obs("2026-03", -1, "regression")])
    assert result["progress"][0]["current_state"] == "persistent_regression"
    assert result["transitions"]

def test_empty_history_is_safe():
    result = ExecutiveProgressTrackingService().history("a", [])
    assert result["tenant_id"] == "a"
    assert result["overall_trajectory"] == "insufficient_data"
