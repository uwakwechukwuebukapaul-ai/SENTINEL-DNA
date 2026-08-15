from services.intelligence.outcome_learning import OutcomeLearningService,OutcomeRecord
def outcome(t="a",fp="confirmed",status="SUCCESS",det="d1"): return OutcomeRecord(t,"l"+det,detection_reference=det,resolution_status="UNKNOWN",verification_status=status,evidence_references=["e1"],false_positive_signal=fp,provenance={"source":"lifecycle"})
def test_outcome_quality_resolution_and_isolation():
    s=OutcomeLearningService(); x=s.record_outcome(outcome()); q=s.evaluate_outcome_quality("a",x.outcome_id); assert s.evaluate_resolution("a",x.outcome_id)=="UNKNOWN" and q.action_effectiveness=="EFFECTIVE" and s.get_historical_outcomes("b")==[]
def test_recurring_advisory_improvement_and_provenance():
    s=OutcomeLearningService(); s.record_outcome(outcome(det="d1")); s.record_outcome(outcome(det="d1")); items=s.generate_improvement_candidates("a"); assert items[0].advisory and items[0].requires_human_review and items[0].provenance
def test_partial_unknown_and_no_mutation():
    s=OutcomeLearningService(); x=s.record_outcome(OutcomeRecord("a","l",verification_status="UNKNOWN")); q=s.evaluate_outcome_quality("a",x.outcome_id); assert q.action_effectiveness=="UNKNOWN" and q.human_review_required and s.get_improvement_candidates("a")==[]
