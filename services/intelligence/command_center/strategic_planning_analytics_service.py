"""Read-only longitudinal interpretation over strategic planning intelligence."""
from .strategic_planning_analytics import StrategicDecisionEffectiveness, StrategicPriorityLifecycle, stable_analytics_id
class StrategicPlanningAnalyticsService:
    ORDER={"reversed":0,"degrading":1,"persistent":2,"recurring":3,"reemerged":4,"emerging":5,"stable":6,"insufficient_history":7}
    def __init__(self,planning_service=None): self.planning_service=planning_service
    def derive(self,tenant_id):
        data=self.planning_service.derive(tenant_id) if self.planning_service else {"priorities":[],"planning":{}}
        lifecycles=[]; effects=[]
        for p in data.get("priorities",[]):
            classification="insufficient_history" if data.get("planning",{}).get("historical_evidence_quality") in ("insufficient_history","limited_history") else ("degrading" if p.get("classification")=="unresolved_priority" else "emerging")
            uid=stable_analytics_id(tenant_id,"lifecycle",p.get("stable_id")); u=tuple(p.get("uncertainty",[]) or [])+(("insufficient_history",) if classification=="insufficient_history" else ())
            lifecycles.append(StrategicPriorityLifecycle(tenant_id,uid,p.get("stable_id"),p.get("title","Priority"),p.get("dimension"),classification,classification,1,0,None,None,p.get("confidence"),p.get("evidence_strength","insufficient"),tuple(sorted(set(u))),p.get("provenance",{}),tuple(p.get("contributing_references",[]))))
            effects.append(StrategicDecisionEffectiveness(tenant_id,stable_analytics_id(tenant_id,"effectiveness",p.get("stable_id")),p.get("stable_id"),"insufficient_evidence","Insufficient temporal evidence to determine effectiveness; observed association is not causation.",None,p.get("confidence"),p.get("evidence_strength","insufficient"),("insufficient_temporal_span",)))
        lifecycles.sort(key=lambda x:(self.ORDER.get(x.classification,99),x.stable_id))
        return {"tenant_id":tenant_id,"analytics":{"planning_status":data.get("planning",{}).get("planning_status","insufficient_history"),"historical_evidence_quality":"insufficient_history" if not lifecycles else data.get("planning",{}).get("historical_evidence_quality","limited_history"),"priority_count":len(lifecycles),"advisory_only":True},"priority_lifecycles":[x.to_dict() for x in lifecycles],"observations":[],"transitions":[],"effectiveness":[x.to_dict() for x in effects],"themes":[],"recommendations":["Collect longitudinal observations before determining strategic effectiveness."],"advisory_only":True}
    def detail(self,tenant_id,signal_id): return next((x for x in self.derive(tenant_id)["priority_lifecycles"] if x["stable_id"]==signal_id),None)
