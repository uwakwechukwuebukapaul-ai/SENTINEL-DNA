from services.intelligence.governance_decision import GovernanceDecisionService
def signal(category="deteriorating_control",tenant="a"):
    return {"category":category,"severity":"high","direction":"deteriorating","confidence":.9,"evidence_references":["e-1"],"source_references":["monitoring:s-1"],"affected_controls":["c-1"],"affected_assets":["asset-1"]}
def test_signals_priorities_rationale_and_provenance():
    service=GovernanceDecisionService(); decisions=service.generate_candidates("a",service.generate_signals("a",[signal()])); assert decisions[0].priority=="high" and decisions[0].requires_human_review and decisions[0].advisory and "e-1" in decisions[0].rationale and decisions[0].provenance
def test_tenant_queue_review_and_dependency_boundary():
    service=GovernanceDecisionService(); a=service.generate_candidates("a",service.generate_signals("a",[signal()])); service.generate_candidates("b",service.generate_signals("b",[signal("evidence_unavailable")])); assert len(service.decision_queue("a"))==1 and service.decision_queue("b")[0].tenant_id=="b"; review=service.record_review("a",a[0].decision_id,"reviewed","human"); assert review.state=="reviewed" and service.decision_queue("a")[0].status=="reviewed" and service.record_review("a","missing","reviewed") is None
def test_determinism_and_no_autonomous_action():
    service=GovernanceDecisionService(); first=service.generate_candidates("a",service.generate_signals("a",[signal()])); second=service.generate_candidates("a",service.generate_signals("a",[signal()])); assert first[0].priority==second[0].priority and all(x.requires_human_review for x in second)
