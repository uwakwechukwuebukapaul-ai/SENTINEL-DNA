from .models import Lifecycle,DecisionRecord,ApprovalRecord,VerificationRecord,LearningRecord,ALLOWED,STATES,now
from .repository import LifecycleRepository
class SOCLifecycleService:
    def __init__(self,repository=None,audit=None): self.repository=repository or LifecycleRepository(); self.audit=audit
    def _audit(self,event,**data):
        if self.audit and hasattr(self.audit,"record"): self.audit.record(event,**data)
    def create_lifecycle(self,tenant_id,case_id="",investigation_id="",availability=None):
        x=Lifecycle(tenant_id,case_id,investigation_id,availability=availability or {}); self.repository.save_lifecycle(x); self.repository.add_history(tenant_id,x.lifecycle_id,{"from":None,"to":"DETECTED","at":x.created_at}); self._audit("lifecycle_created",tenant_id=tenant_id,lifecycle_id=x.lifecycle_id); return x
    def transition(self,tenant_id,lifecycle_id,state):
        x=self.repository.get_lifecycle(tenant_id,lifecycle_id)
        if x is None: return None
        if state not in STATES or state not in ALLOWED.get(x.state,set()): raise ValueError("invalid lifecycle transition")
        old=x.state; x.state=state; x.updated_at=now(); self.repository.save_lifecycle(x); self.repository.add_history(tenant_id,lifecycle_id,{"from":old,"to":state,"at":x.updated_at}); self._audit("lifecycle_transitioned",tenant_id=tenant_id,lifecycle_id=lifecycle_id,state=state); return x
    def record_decision(self,record): self.repository.save_decision(record); self._audit("decision_recorded",tenant_id=record.tenant_id,lifecycle_id=record.lifecycle_id); return record
    def request_approval(self,tenant_id,lifecycle_id):
        x=self.repository.get_lifecycle(tenant_id,lifecycle_id); return self.repository.save_approval(ApprovalRecord(tenant_id,lifecycle_id)) if x else None
    def record_approval(self,tenant_id,lifecycle_id,status,reviewer_reference="",rationale=""):
        if status not in {"approved","rejected","expired","cancelled"}: raise ValueError("invalid approval status")
        return self.repository.save_approval(ApprovalRecord(tenant_id,lifecycle_id,status,reviewer_reference,rationale))
    def record_action_request(self,tenant_id,lifecycle_id,requested_action):
        return self.repository.save_action(tenant_id,lifecycle_id,{"requested_action":requested_action,"authorization_state":"pending","executed":False,"advisory":True})
    def record_execution_reference(self,tenant_id,lifecycle_id,execution_reference,result_reference=""):
        return self.repository.save_action(tenant_id,lifecycle_id,{"execution_reference":execution_reference,"result_reference":result_reference,"executed":bool(execution_reference),"external_execution_by_lifecycle":False})
    def record_verification(self,record):
        if record.status not in {"NOT_STARTED","IN_PROGRESS","SUCCESS","PARTIAL","FAILED","UNKNOWN"}: raise ValueError("invalid verification status")
        return self.repository.save_verification(record)
    def record_learning_outcome(self,record): return self.repository.save_learning(record)
    def get_lifecycle(self,tenant_id,lifecycle_id): return self.repository.get_lifecycle(tenant_id,lifecycle_id)
    def get_history(self,tenant_id,lifecycle_id): return self.repository.get_history(tenant_id,lifecycle_id)
    def close_lifecycle(self,tenant_id,lifecycle_id): return self.transition(tenant_id,lifecycle_id,"CLOSED")
