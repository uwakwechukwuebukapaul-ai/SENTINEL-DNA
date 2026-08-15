"""Deterministic, non-persistent strategic planning aggregation."""
from .strategic_planning import StrategicPlanningPosture, StrategicPlanningPriority, stable_planning_id

class StrategicPlanningService:
    ORDER={"priority_reversal":0,"unresolved_priority":1,"recurring_priority":2,"emerging_priority":3,"stable_strategy":4,"insufficient_history":5}
    def __init__(self,strategy_service=None,progress_service=None,scenario_service=None,matrix_service=None): self.strategy_service,self.progress_service,self.scenario_service,self.matrix_service=strategy_service,progress_service,scenario_service,matrix_service
    def _base(self,tenant): return self.strategy_service.derive(tenant) if self.strategy_service else {"tenant_id":tenant,"strategic_signals":[],"posture":{}}
    def derive(self,tenant_id):
        base=self._base(tenant_id); signals=[x for x in base.get("strategic_signals",[]) if x.get("tenant_id",tenant_id)==tenant_id]; priorities=[]
        for x in signals:
            kind="unresolved_priority" if x.get("signal_type") in ("regression","persistent_quality_issue","improvement_program_risk") else "sustained_priority" if x.get("signal_type")=="sustained_improvement" else "emerging_priority" if x.get("signal_type")=="insufficient_evidence" else "stable_strategy"
            priorities.append(StrategicPlanningPriority(tenant_id,stable_planning_id(tenant_id,"priority",x.get("signal_id")),kind,x.get("title","Strategic signal"),x.get("organizational_dimension"),x.get("priority","medium"),x.get("description","Backend-derived strategic signal."),x.get("evidence_strength","insufficient"),x.get("confidence"),tuple(x.get("uncertainty",[]) or []),x.get("provenance",{}),tuple(x.get("contributing_references",[]) or []),"Review observed evidence and limitations.",x.get("recommended_focus","Continue advisory measurement.")))
        priorities.sort(key=lambda x:(self.ORDER.get(x.classification,99),x.priority,x.stable_id)); ids=lambda c:tuple(x.stable_id for x in priorities if x.classification==c)
        p=base.get("posture",{}); history_status="limited_history" if not priorities else "insufficient_history"; status="actionable" if any(x.classification=="unresolved_priority" for x in priorities) else "monitoring" if priorities else "insufficient_history"
        posture=StrategicPlanningPosture(status,p.get("posture","insufficient_data"),priorities[0].dimension if priorities else None,None,None,ids("recurring_priority"),ids("sustained_priority"),ids("unresolved_priority"),ids("resolved_priority"),ids("priority_reversal"),tuple(),history_status,p.get("confidence"),tuple(["insufficient_history"] if not priorities else []))
        scenario_refs=[]; matrix_refs=[]
        if self.scenario_service: scenario_refs=["evaluated scenario templates are hypothetical and not decision history"]
        return {"tenant_id":tenant_id,"planning":posture.to_dict(),"priorities":[x.to_dict() for x in priorities],"history":[],"themes":[],"recommendations":[x.recommendation for x in priorities],"scenario_references":scenario_refs,"decision_matrix_references":matrix_refs,"advisory_only":True}
    def detail(self,tenant_id,signal_id):
        data=self.derive(tenant_id); found=next((x for x in data["priorities"] if x["stable_id"]==signal_id),None); return found
