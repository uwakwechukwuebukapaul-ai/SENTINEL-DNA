from services.intelligence.command_center.executive_strategy_service import ExecutiveStrategyService

def test_strategy_is_deterministic_and_tenant_scoped():
    service=ExecutiveStrategyService()
    data={"maturity":{},"report":{"current_score":72,"current_level":"developing","trajectory":"improving"},"programs":{},"outcomes":{},"progress":{"progress":[{"tenant_id":"a","program_id":"p","dimension":"detection","current_state":"regression","current_score":40,"trajectory":"degrading","confidence":.8,"evidence_strength":"strong","uncertainty":[],"provenance":{"source":"test"},"contributing_references":[]}]},"learning":[]}
    first=service.derive("a",data); assert first==service.derive("a",data); assert first["posture"]["posture"]=="degrading"; assert first["strategic_signals"][0]["signal_type"]=="regression"; assert service.derive("b",data)["tenant_id"]=="b"

def test_strategy_handles_empty_evidence():
    result=ExecutiveStrategyService().derive("tenant",{"maturity":{},"report":{},"programs":{},"outcomes":{},"progress":{},"learning":[]})
    assert result["posture"]["posture"]=="insufficient_data"; assert result["advisory_only"] is True
