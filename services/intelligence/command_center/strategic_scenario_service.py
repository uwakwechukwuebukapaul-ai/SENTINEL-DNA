"""Read-only, bounded scenario analysis over existing executive intelligence."""
from .strategic_scenario import StrategicScenario, stable_scenario_id

class StrategicScenarioService:
    TYPES={"maturity_improvement":"Assume the identified target dimension improves by one maturity state.","quality_improvement":"Assume investigation quality improves based on the available evidence.","regression_reduction":"Assume observed regression frequency decreases.","learning_effectiveness":"Assume analyst learning effectiveness strengthens.","sustainability_improvement":"Assume observed improvement becomes sustained.","organizational_learning":"Assume the identified organizational learning issue is addressed.","program_prioritization":"Assume the selected improvement program reaches its stated measurement target."}
    def __init__(self, strategy_service=None, progress_service=None): self.strategy_service=strategy_service; self.progress_service=progress_service
    @staticmethod
    def _v(x,k,d=None): return x.get(k,d) if isinstance(x,dict) else getattr(x,k,d)
    def _base(self,tenant): return self.strategy_service.derive(tenant) if self.strategy_service else {"tenant_id":tenant,"posture":{},"strategic_signals":[],"advisory_only":True}
    def options(self,tenant_id):
        base=self._base(tenant_id); dims=sorted({self._v(x,"organizational_dimension") for x in base.get("strategic_signals",[]) if self._v(x,"organizational_dimension")})
        return {"tenant_id":tenant_id,"scenarios":[{"scenario_type":k,"title":k.replace("_"," ").title(),"assumption":v,"target_dimensions":dims,"supported":bool(dims or k in ("regression_reduction","learning_effectiveness"))} for k,v in self.TYPES.items() if dims or k in ("regression_reduction","learning_effectiveness")],"advisory_only":True}
    def evaluate(self,tenant_id,payload):
        if not isinstance(payload,dict): raise ValueError("invalid_scenario")
        kind=payload.get("scenario_type"); target=payload.get("target_dimension"); assumption=payload.get("assumption")
        if kind not in self.TYPES: raise ValueError("unsupported_scenario")
        if not isinstance(assumption,str) or not assumption.strip() or len(assumption)>500: raise ValueError("invalid_assumption")
        base=self._base(tenant_id); signals=[x for x in base.get("strategic_signals",[]) if not target or self._v(x,"organizational_dimension")==target]
        if target and not signals: raise ValueError("unsupported_dimension")
        posture=base.get("posture",{}); score=posture.get("maturity_score"); state=posture.get("posture","insufficient_data"); uncertainty=list(posture.get("uncertainty",[]) or []); evidence=posture.get("evidence_strength","insufficient"); confidence="high" if evidence in ("strong","high") else "medium" if evidence in ("moderate","medium") else "low" if evidence not in ("insufficient",None) else "insufficient"
        if score is None: scenario_score=None; delta=None; scenario_state="not_measurable"; classification="insufficient_evidence"; uncertainty.append("scenario_not_directly_measurable")
        else:
            delta=7 if kind in ("maturity_improvement","quality_improvement","learning_effectiveness","sustainability_improvement","organizational_learning","program_prioritization") else 5 if kind=="regression_reduction" else 0
            scenario_score=round(max(0,min(100,score+delta)),2); scenario_state="improving" if delta>0 else state; classification="favorable" if delta>0 else "neutral"
        refs=sorted({r for x in signals for r in (self._v(x,"contributing_references",[]) or [])})
        return StrategicScenario(tenant_id,stable_scenario_id(tenant_id,kind,target,assumption),kind,kind.replace("_"," ").title(),"Deterministic hypothetical overlay on the observed executive state.",assumption,"strategic planning",target,state,scenario_state,score,scenario_score,delta,posture.get("maturity_trajectory","unavailable"),"improving" if delta and delta>0 else posture.get("maturity_trajectory","unavailable"),classification,confidence,evidence,tuple(sorted(set(uncertainty))),{"source":"strategic_scenario","upstream":["executive_strategy"],"tenant_id":tenant_id},tuple(refs),"Use this scenario for advisory prioritization only; it does not predict or establish causation.").to_dict()
