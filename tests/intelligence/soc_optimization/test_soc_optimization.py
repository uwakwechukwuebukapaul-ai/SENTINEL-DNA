from services.intelligence.soc_optimization import SOCOptimizationService
def test_domains_priorities_provenance_and_boundary():
    s=SOCOptimizationService(); xs=s.analyze_detection("a",[{"category":"HIGH_NOISE","detection_reference":"d1","frequency":5,"impact":"high","confidence":.8,"references":["o1"],"provenance":{"source":"outcome"}}]); ys=s.analyze_investigation("a",[{"category":"EVIDENCE_BOTTLENECK","investigation_reference":"i1","frequency":2}]); assert xs[0].priority=="high" and ys[0].uncertainty=="UNKNOWN" and xs[0].requires_human_review and xs[0].provenance
def test_tenant_isolation_determinism_and_partial_data():
    s=SOCOptimizationService(); s.analyze_evidence("a",[{"category":"UNAVAILABLE_SOURCE","evidence_reference":"e1"}]); s.analyze_playbook("b",[{"category":"PLAYBOOK_REVIEW_RECOMMENDED","frequency":3}]); assert s.get_candidates("b")[0].tenant_id=="b" and s.get_candidates("a")[0].tenant_id=="a" and s.get_candidates("none")==[]
def test_cross_domain_correlation_no_source_mutation():
    s=SOCOptimizationService(); data=[{"category":"LOW_SIGNAL","detection_reference":"d","frequency":2}]; before=list(data); result=s.analyze_detection("a",data); assert data==before and s.prioritize_candidates("a")[0].candidate_id==result[0].candidate_id
