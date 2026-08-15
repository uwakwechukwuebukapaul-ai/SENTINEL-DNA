import pytest
from services.intelligence.lifecycle import SOCLifecycleService,DecisionRecord,VerificationRecord,LearningRecord
def test_lifecycle_transitions_and_invalid_rejection():
    s=SOCLifecycleService(); x=s.create_lifecycle("a","c","i"); s.transition("a",x.lifecycle_id,"INVESTIGATING"); s.transition("a",x.lifecycle_id,"UNDERSTOOD");
    with pytest.raises(ValueError): s.transition("a",x.lifecycle_id,"VERIFIED")
def test_decision_approval_action_verification_learning_and_isolation():
    s=SOCLifecycleService(); x=s.create_lifecycle("a"); d=s.record_decision(DecisionRecord("a",x.lifecycle_id,evidence_references=["e1"],requires_human_review=True)); approval=s.request_approval("a",x.lifecycle_id); assert d.requires_human_review and approval.status=="approval_required" and s.get_lifecycle("b",x.lifecycle_id) is None
    s.record_approval("a",x.lifecycle_id,"approved","human"); action=s.record_action_request("a",x.lifecycle_id,"review"); assert action["executed"] is False; v=s.record_verification(VerificationRecord("a",x.lifecycle_id,"UNKNOWN")); l=s.record_learning_outcome(LearningRecord("a",x.lifecycle_id,decision_reference=d.decision_id)); assert v.status=="UNKNOWN" and l.verification_outcome=="UNKNOWN"
def test_history_and_partial_execution_boundary():
    s=SOCLifecycleService(); x=s.create_lifecycle("a",availability={"execution":{"available":False}}); s.record_execution_reference("a",x.lifecycle_id,"exec-1"); assert s.get_history("a",x.lifecycle_id)[0]["to"]=="DETECTED" and s.repository.actions[("a",x.lifecycle_id)]["external_execution_by_lifecycle"] is False
