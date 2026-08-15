"""Deterministic, read-only improvement program outcome measurement."""
from .improvement_program import ImprovementProgram, stable_program_id

STATUS_ORDER = {"degrading": 0, "improving": 1, "completed": 2, "stalled": 3, "mixed": 4, "stable": 5, "not_yet_measurable": 6, "insufficient_data": 7}
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4, "insufficient_data": 5}


class ImprovementProgramAnalyticsService:
    def __init__(self, maturity_service=None, reporting_service=None, improvement_service=None): self.maturity_service, self.reporting_service, self.improvement_service = maturity_service, reporting_service, improvement_service
    @staticmethod
    def _v(x, k, d=None): return x.get(k, d) if isinstance(x, dict) else getattr(x, k, d)

    def derive(self, tenant_id, improvement=None, maturity=None, report=None):
        improvement = improvement if improvement is not None else (self.improvement_service.derive(tenant_id) if self.improvement_service else {})
        maturity = maturity if maturity is not None else (self.maturity_service.derive(tenant_id) if self.maturity_service else None)
        report = report if report is not None else (self.reporting_service.derive(tenant_id, current=maturity) if self.reporting_service else None)
        priorities = [x for x in (improvement.get("priority_signals", []) if isinstance(improvement, dict) else []) if self._v(x, "tenant_id", tenant_id) == tenant_id]
        plans = {self._v(x, "dimension_id"): x for x in (improvement.get("improvement_plans", []) if isinstance(improvement, dict) else []) if self._v(x, "tenant_id", tenant_id) == tenant_id}
        dimensions = {self._v(x, "dimension_id"): x for x in (improvement.get("comparative_dimensions", []) if isinstance(improvement, dict) else []) if self._v(x, "tenant_id", tenant_id) == tenant_id}
        programs=[]
        for priority in priorities:
            dim = self._v(priority, "dimension_id", "unknown"); plan=plans.get(dim, {}); d=dimensions.get(dim, {})
            current=self._v(d, "current_score_or_state"); baseline=None; target=None; delta=None
            uncertainty=list(self._v(priority, "uncertainty", []) or [])
            if current is None or not isinstance(current, (int, float)): status="not_yet_measurable"; uncertainty.append("outcome not yet measurable")
            else: status="completed" if self._v(priority,"current_state")=="strong" else "improving" if self._v(priority,"trend")=="improving" else "degrading" if self._v(priority,"trend")=="degrading" else "stalled" if self._v(priority,"trend")=="stable" else "stable"
            if status == "not_yet_measurable": effectiveness="indeterminate"; progress=None; outcome="No numeric outcome can be measured from the available evidence."
            else: effectiveness="effective" if status in ("completed","improving") else "ineffective" if status=="degrading" else "indeterminate"; progress=None; outcome="Observed movement is associated with the improvement program; causation is not established."
            programs.append(ImprovementProgram(tenant_id, stable_program_id(tenant_id, dim), self._v(priority,"dimension_name",dim), self._v(priority,"priority","insufficient_data"), status, status, baseline, current, delta, target, progress, self._v(priority,"trend","insufficient_data"), outcome, effectiveness, self._v(priority,"confidence"), self._v(priority,"evidence_strength","insufficient"), sorted(set(uncertainty)), {"source":"improvement_program_analytics","upstream":["organizational_maturity","maturity_reporting","maturity_improvement"],"tenant_id":tenant_id}, sorted(set(self._v(priority,"contributing_references",[]) or [])), "", "", "", self._v(plan,"recommended_focus","Collect additional evidence.")))
        programs.sort(key=lambda x:(PRIORITY_ORDER.get(x.priority,99),STATUS_ORDER.get(x.status,99),x.dimension,x.program_id))
        counts={s:sum(x.status==s for x in programs) for s in STATUS_ORDER}; summary={"total_programs":len(programs),**{f"{s}_programs":n for s,n in counts.items()},"overall_progress":None if not programs else "insufficient_data" if all(x.status=="not_yet_measurable" for x in programs) else "mixed","overall_effectiveness":"indeterminate","highest_priority_area":programs[0].dimension if programs else None,"strongest_improvement_area":None,"weakest_improvement_area":programs[0].dimension if programs else None,"executive_recommendation":"Collect additional evidence before evaluating improvement outcomes." if not programs or all(x.effectiveness=="indeterminate" for x in programs) else programs[0].recommendation}
        return {"tenant_id":tenant_id,"programs":[x.to_dict() for x in programs],"summary":summary,"advisory_only":True}
