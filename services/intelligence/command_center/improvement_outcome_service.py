"""Read-only outcome measurement over canonical improvement programs."""
from .improvement_outcome import ExecutiveImprovementProgress, ImprovementProgramOutcome, stable_outcome_id

ORDER={"degrading":0,"regression":1,"meaningful_improvement":2,"sustained_improvement":3,"partial_improvement":4,"stalled":5,"mixed":6,"stable":7,"not_yet_measurable":8,"insufficient_data":9,"indeterminate":10}


class ImprovementOutcomeIntelligenceService:
    def __init__(self, program_service=None, maturity_service=None, reporting_service=None): self.program_service,self.maturity_service,self.reporting_service=program_service,maturity_service,reporting_service
    @staticmethod
    def _v(x,k,d=None): return x.get(k,d) if isinstance(x,dict) else getattr(x,k,d)
    def derive(self, tenant_id, program_data=None):
        data=program_data if program_data is not None else (self.program_service.derive(tenant_id) if self.program_service else {})
        programs=[x for x in (data.get("programs",[]) if isinstance(data,dict) else []) if self._v(x,"tenant_id",tenant_id)==tenant_id]
        results=[]
        for p in programs:
            current=self._v(p,"current_score"); baseline=self._v(p,"baseline_score"); target=self._v(p,"target_score"); delta=self._v(p,"score_delta")
            if current is None or not isinstance(current,(int,float)): outcome="not_yet_measurable"; effectiveness="indeterminate"; progress=None; uncertainty=["outcome not yet measurable"]
            elif delta is not None and delta>0: outcome="meaningful_improvement"; effectiveness="effective"; progress=100.0 if target is not None and current>=target else None; uncertainty=[]
            elif delta is not None and delta<0: outcome="regression"; effectiveness="ineffective"; progress=0.0; uncertainty=[]
            else: outcome="stable"; effectiveness="indeterminate"; progress=None; uncertainty=["insufficient historical observations"]
            results.append(ImprovementProgramOutcome(tenant_id,stable_outcome_id(tenant_id,self._v(p,"program_id","unknown")),self._v(p,"dimension","unknown"),self._v(p,"priority","insufficient_data"),self._v(p,"status","insufficient_data"),outcome,outcome,baseline,self._v(p,"prior_score"),current,target,delta,progress,"unavailable",self._v(p,"trajectory","insufficient_data"),"insufficient_data",outcome=="regression",effectiveness,"moderate" if current is not None else "insufficient",self._v(p,"confidence"),self._v(p,"evidence_strength","insufficient"),uncertainty,self._v(p,"measurement_window",""),self._v(p,"baseline_period",""),self._v(p,"prior_period",""),self._v(p,"current_period",""),self._v(p,"provenance",{}),self._v(p,"contributing_references",[]),"Continue monitoring observed outcomes; association does not establish causation."))
        results.sort(key=lambda x:(self._v(x,"priority","insufficient_data"),ORDER.get(x.outcome_classification,99),x.dimension,x.program_id))
        counts={k:sum(x.outcome_classification==k for x in results) for k in ORDER}; total=len(results); improving=counts["meaningful_improvement"]+counts["sustained_improvement"]; regressions=counts["regression"]+counts["degrading"]
        score=round(max(0,min(100,100*improving/total-50*regressions/total)),2) if total else None
        summary=ExecutiveImprovementProgress(tenant_id,total,counts["meaningful_improvement"],counts["sustained_improvement"],counts["partial_improvement"],counts["stable"],counts["stalled"],regressions,counts["degrading"],counts["insufficient_data"]+counts["not_yet_measurable"],score,"effective" if improving and not regressions else "ineffective" if regressions and not improving else "indeterminate","unavailable",results[0].dimension if improving else None,results[-1].dimension if results else None,results[0].dimension if regressions else None,round(counts["sustained_improvement"]/total,6) if total else None,None,"insufficient" if not results else "moderate",["outcome not yet measurable"] if not results or all(x.effectiveness=="indeterminate" for x in results) else [],{"source":"improvement_outcome","upstream":["improvement_program_analytics","maturity_reporting"],"tenant_id":tenant_id},["Collect additional historical observations before evaluating outcomes."] if not results or not improving else ["Continue successful programs and monitor sustained improvement."])
        return {"tenant_id":tenant_id,"outcomes":[x.to_dict() for x in results],"summary":summary.to_dict(),"advisory_only":True}
