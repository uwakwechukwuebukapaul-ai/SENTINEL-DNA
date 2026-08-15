"""Read-only, tenant-scoped temporal progress tracking."""
from .progress_tracking import *

class ExecutiveProgressTrackingService:
    def __init__(self, outcome_service=None, *_, minimum_sustained_observations=3): self.outcome_service=outcome_service; self.minimum_sustained_observations=minimum_sustained_observations
    @staticmethod
    def _v(x,k,d=None): return x.get(k,d) if isinstance(x,dict) else getattr(x,k,d)
    def _observations(self, tenant_id, observations):
        result=[]
        for raw in observations or []:
            if self._v(raw,"tenant_id",tenant_id)!=tenant_id: continue
            period=self._v(raw,"observation_period",self._v(raw,"current_period"))
            result.append(ExecutiveProgressObservation(tenant_id,self._v(raw,"program_id","unknown"),self._v(raw,"dimension","unknown"),period,self._v(raw,"state",self._v(raw,"outcome_classification","indeterminate")),self._v(raw,"score",self._v(raw,"current_score")),self._v(raw,"score_delta"),self._v(raw,"progress_percentage"),self._v(raw,"trajectory","unavailable"),self._v(raw,"effectiveness","indeterminate"),self._v(raw,"confidence"),self._v(raw,"evidence_strength","insufficient"),tuple(self._v(raw,"uncertainty",[]) or []),self._v(raw,"provenance",{}) or {},tuple(self._v(raw,"contributing_references",[]) or [])))
        return sorted({x.stable_id:x for x in result}.values(), key=lambda x:(x.observation_period is None,x.observation_period or "",x.dimension,x.program_id,x.stable_id))
    def track(self, tenant_id, observations=None):
        groups={}
        for o in self._observations(tenant_id, observations): groups.setdefault((o.program_id,o.dimension),[]).append(o)
        results=[]; transitions=[]
        for (pid,dim), obs in sorted(groups.items()):
            valid=[o for o in obs if o.observation_period is not None]; states=[o.state for o in valid]
            if not obs: state="new"
            elif len(valid)<2: state="insufficient_data" if not valid else ("not_yet_measurable" if valid[-1].score is None else valid[-1].state)
            elif sum(s in ("regression","degrading") for s in states[-2:])>=2: state="persistent_regression"
            elif states[-1] in ("regression","degrading") and any(s in ("improving","sustained_improvement") for s in states[:-1]): state=states[-1]
            elif len(valid)>=self.minimum_sustained_observations and all(o.score_delta is not None and o.score_delta>0 for o in valid[-self.minimum_sustained_observations:]): state="sustained_improvement"
            elif valid[-1].score_delta is not None and valid[-1].score_delta>0: state="improving"
            elif valid[-1].score_delta is not None and valid[-1].score_delta<0: state="degrading"
            else: state=valid[-1].state if valid[-1].state in STATES else "indeterminate"
            for prev,cur in zip(valid,valid[1:]):
                if prev.state!=cur.state: transitions.append(ExecutiveProgressTransition(tenant_id,pid,dim,prev.state,cur.state,f"{prev.state}_to_{cur.state}" if f"{prev.state}_to_{cur.state}" in {"improving_to_sustained","improving_to_stable","improving_to_stalled","improving_to_regression","sustained_improvement_to_regression","regression_to_persistent_regression","regression_to_recovery","persistent_regression_to_recovery","recovery_to_improving","recovery_to_sustained","stalled_to_improving","stalled_to_regression"} else "state_change",cur.observation_period,cur.score_delta,cur.confidence,cur.evidence_strength,cur.uncertainty,cur.provenance,cur.contributing_references))
            latest=valid[-1] if valid else obs[-1]; baseline=valid[0].score if valid else None; delta=None if baseline is None or latest.score is None else latest.score-baseline
            sustain="sustained" if state=="sustained_improvement" else "fragile" if state=="improving" else "unsustained" if state in ("regression","persistent_regression") else "insufficient_data" if len(valid)<2 else "fragile"
            rec=("Escalate executive attention and reassess program assumptions." if state=="persistent_regression" else "Investigate regression drivers and review recent changes." if state in ("regression","degrading") else "Preserve current practice and continue measurement." if state=="sustained_improvement" else "Review program execution and measurement criteria." if state=="stalled" else "Continue measurement and validate durability.")
            results.append(ExecutiveProgressTracking(tenant_id,pid,dim,state,valid[-2].state if len(valid)>1 else None,"mixed" if len(set(states))>2 else latest.trajectory,latest.score,baseline,latest.score,delta,"unavailable",sustain,"persistent" if state=="persistent_regression" else "temporary" if state in ("regression","degrading") else "none","recovery" if state=="recovery" else "no_recovery",len(obs),len([t for t in transitions if t.program_id==pid]),valid[0].observation_period if valid else None,latest.observation_period if valid else None,latest.confidence,latest.evidence_strength,tuple(sorted(set(sum((list(o.uncertainty) for o in obs),[])))),latest.provenance,tuple(sorted(set(sum((list(o.contributing_references) for o in obs),[])))),(rec,)))
        return {"tenant_id":tenant_id,"progress":[x.to_dict() for x in results],"transitions":[x.to_dict() for x in transitions],"summary":{"observation_count":sum(x.observation_count for x in results),"transition_count":len(transitions)},"advisory_only":True}
    def derive(self, tenant_id, observations=None):
        if observations is None and self.outcome_service: data=self.outcome_service.derive(tenant_id); observations=data.get("outcomes",[])
        return self.track(tenant_id, observations)
    def history(self, tenant_id, observations=None):
        data=self.derive(tenant_id,observations); progress=data["progress"]; periods=tuple(sorted({p for x in progress for p in (x.get("first_observed_period"),x.get("last_observed_period")) if p})); scores=tuple(x.get("current_score") for x in progress if x.get("current_score") is not None); current=scores[-1] if scores else None; previous=scores[-2] if len(scores)>1 else None
        h=ExecutiveProgressHistory(tenant_id,periods,scores,"improving" if current is not None and previous is not None and current>previous else "stable" if current is not None else "insufficient_data",current,previous,None if current is None or previous is None else current-previous,"unavailable",None,None,None,tuple(x["program_id"] for x in progress if x["current_state"]=="improving"),tuple(x["program_id"] for x in progress if x["current_state"]=="sustained_improvement"),tuple(x["program_id"] for x in progress if x["current_state"]=="stalled"),tuple(x["program_id"] for x in progress if "regression" in x["current_state"]),tuple(x["program_id"] for x in progress if x["current_state"]=="recovery"),None,None,next((x["dimension"] for x in progress if "regression" in x["current_state"]),None),None,"insufficient" if not progress else "moderate",(),{"source":"executive_progress_tracking","upstream":["improvement_outcomes"],"tenant_id":tenant_id},("Temporal progress is advisory and does not establish causation.",))
        return h.to_dict()
