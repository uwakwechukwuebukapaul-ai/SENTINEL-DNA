"""Deterministic read-only composition of executive intelligence."""
from .executive_strategy import ExecutivePosture, StrategicScorecardItem, StrategicSignal, stable_strategy_id

class ExecutiveStrategyService:
    ORDER={"regression":0,"maturity_decline":1,"improvement_program_risk":2,"persistent_quality_issue":3,"degrading_learning":4,"unresolved_quality_issue":5,"insufficient_evidence":6,"mixed_signal":7,"sustained_improvement":8,"recovery":9,"maturity_improvement":10,"strategic_strength":11}
    def __init__(self, maturity=None, reporting=None, improvement=None, programs=None, outcomes=None, progress=None, learning=None, trends=None, effectiveness=None, executive_learning=None): self.services=(maturity,reporting,improvement,programs,outcomes,progress,learning,trends,effectiveness,executive_learning)
    @staticmethod
    def _v(x,k,d=None): return x.get(k,d) if isinstance(x,dict) else getattr(x,k,d)
    def _derive(self, service, tenant, default=None):
        try: return service.derive(tenant) if service else default
        except (AttributeError,TypeError,ValueError): return default
    def derive(self, tenant_id, data=None):
        if data is None:
            maturity=self._derive(self.services[0],tenant_id,{})
            report=self._derive(self.services[1],tenant_id,{})
            programs=self._derive(self.services[3],tenant_id,{})
            outcomes=self._derive(self.services[4],tenant_id,{})
            progress=self._derive(self.services[5],tenant_id,{})
            learning=self._derive(self.services[6],tenant_id,[])
        else: maturity,report,programs,outcomes,progress,learning=(data.get(k,{}) for k in ("maturity","report","programs","outcomes","progress","learning"))
        maturity=maturity.to_dict() if hasattr(maturity,"to_dict") else maturity; report=report.to_dict() if hasattr(report,"to_dict") else report
        signals=[]; uncertainty=[]
        score=self._v(report,"current_score",self._v(maturity,"score")); trajectory=self._v(report,"trajectory",self._v(maturity,"trajectory","insufficient_data"))
        for item in (progress.get("progress",[]) if isinstance(progress,dict) else []):
            state=self._v(item,"current_state","indeterminate"); kind="regression" if "regression" in state or state=="degrading" else "sustained_improvement" if state=="sustained_improvement" else "recovery" if state=="recovery" else "strategic_strength" if state=="improving" else "insufficient_evidence"
            signals.append(StrategicSignal(tenant_id,stable_strategy_id(tenant_id,kind,self._v(item,"program_id"),self._v(item,"dimension")),kind,(self._v(item,"dimension","Unknown")+" progress"),("Backend-derived temporal state: "+state),"high" if kind=="regression" else "medium", "high" if kind=="regression" else None,"improvement",self._v(item,"dimension"),state,self._v(item,"trajectory","unavailable"),self._v(item,"current_score"),self._v(item,"confidence"),self._v(item,"evidence_strength","insufficient"),tuple(self._v(item,"uncertainty",[]) or []),self._v(item,"provenance",{}) or {},tuple(self._v(item,"contributing_references",[]) or []),"Review the observed program evidence; recommendations remain advisory."))
        if trajectory in ("degrading","regressing","sustained_degrading"):
            signals.append(StrategicSignal(tenant_id,stable_strategy_id(tenant_id,"maturity_decline"),"maturity_decline","Maturity trajectory is declining","The maturity reporting service observes a declining trajectory.","high","high","maturity",None,self._v(report,"current_level"),trajectory,score,self._v(report,"confidence"),self._v(report,"evidence_strength","insufficient"),tuple(self._v(report,"uncertainty",[]) or []),self._v(report,"provenance",{}) or {},tuple(self._v(report,"contributing_references",[]) or []),"Review maturity evidence and improvement priorities."))
        signals.sort(key=lambda x:(self.ORDER.get(x.signal_type,99),-({"high":2,"medium":1,"low":0}.get(x.priority,0)),x.signal_id))
        regress=[x for x in signals if x.signal_type=="regression"]; sustained=[x for x in signals if x.signal_type=="sustained_improvement"]
        posture="degrading" if regress or trajectory in ("degrading","regressing") else "improving" if sustained or trajectory in ("improving","accelerating") else "stable" if score is not None else "insufficient_data"
        p=ExecutivePosture(posture,"Backend-derived maturity and temporal progress signals." if signals else "Insufficient evidence for executive posture.",self._v(report,"current_level"),score,trajectory,self._v(progress,"summary",{}).get("overall_state","insufficient_data") if isinstance(progress,dict) else "insufficient_data","persistent" if any(self._v(x,"current_state")=="persistent_regression" for x in (progress.get("progress",[]) if isinstance(progress,dict) else [])) else "none","sustained" if sustained else "insufficient_data",self._v(report,"confidence"),self._v(report,"evidence_strength","insufficient"),tuple(sorted(set(uncertainty))),True)
        scorecard=[StrategicScorecardItem("maturity",score,self._v(report,"current_level","unavailable"),trajectory,self._v(report,"confidence"),self._v(report,"evidence_strength","insufficient"),tuple(self._v(report,"uncertainty",[]) or []),self._v(report,"provenance",{}) or {}),StrategicScorecardItem("sustainability",None,"sustained" if sustained else "insufficient_data","unavailable",None,"insufficient",("No canonical aggregate sustainability score is available.",),{"source":"progress_tracking"})]
        priorities=[{"priority_id":x.signal_id,"title":x.title,"rationale":x.description,"strategic_area":x.strategic_area,"priority_level":x.priority,"evidence_strength":x.evidence_strength,"confidence":x.confidence,"uncertainty":list(x.uncertainty),"contributing_references":list(x.contributing_references),"recommended_focus":x.recommended_focus,"advisory_only":True} for x in signals[:5]]
        return {"tenant_id":tenant_id,"posture":p.to_dict(),"scorecard":[x.to_dict() for x in scorecard],"strategic_signals":[x.to_dict() for x in signals],"priorities":priorities,"summary":{"summary":"Evidence-backed executive improvement intelligence; observed association does not establish causation.","key_strengths":[x.title for x in sustained],"key_risks":[x.title for x in regress],"emerging_patterns":[],"improvement_opportunities":[x.title for x in signals if x.signal_type in ("insufficient_evidence","regression")],"evidence_limitations":list(p.uncertainty),"recommended_focus":priorities[0]["recommended_focus"] if priorities else "Collect additional evidence before strategic interpretation.","confidence":p.confidence,"uncertainty":list(p.uncertainty)},"organizational_dimensions":[],"advisory_only":True}
