"""Deterministic comparative maturity and advisory planning aggregation."""
from .maturity_improvement import ComparativeDimension, ImprovementPlan, ImprovementPriority, stable_improvement_id

PRIORITY = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4, "insufficient_data": 5}


class MaturityImprovementService:
    def __init__(self, maturity_service=None, reporting_service=None): self.maturity_service, self.reporting_service = maturity_service, reporting_service
    @staticmethod
    def _v(x, k, d=None): return x.get(k, d) if isinstance(x, dict) else getattr(x, k, d)
    @classmethod
    def _refs(cls, x): return sorted({str(v) for v in (cls._v(x, "contributing_references", []) or []) if v not in (None, "")})

    def derive(self, tenant_id, maturity=None, report=None):
        maturity = maturity if maturity is not None else (self.maturity_service.derive(tenant_id) if self.maturity_service else None)
        report = report if report is not None else (self.reporting_service.derive(tenant_id, current=maturity) if self.reporting_service else None)
        if not report: return {"tenant_id": tenant_id, "current_maturity": {}, "comparative_dimensions": [], "priority_signals": [], "improvement_plans": [], "executive_summary": {"classification": "insufficient_evidence"}, "advisory_only": True}
        summaries = self._v(report, "dimension_summaries", []) or []
        scores = [self._v(x, "score") for x in summaries if self._v(x, "score") is not None]
        ordered = sorted(summaries, key=lambda x: (-float(self._v(x, "score", -1)), str(self._v(x, "dimension_id", ""))))
        dimensions = []
        for i, item in enumerate(ordered):
            score = self._v(item, "score"); classification = self._v(item, "classification", "insufficient_data")
            direction = "improving" if classification in ("improving", "positive_quality_pattern") else "degrading" if classification in ("degrading", "quality_degradation", "persistent_pattern") else "stable" if score is not None else "insufficient_data"
            position = "unavailable" if score is None else "leading" if i < max(1, len(ordered)//3) else "lagging" if i >= max(1, len(ordered)*2//3) else "middle"
            dimensions.append(ComparativeDimension(tenant_id, str(self._v(item, "dimension_id", "unknown")), self._v(item, "display_name", self._v(item, "title", "Dimension")), score if score is not None else classification, None, None, direction, position, classification, self._v(item, "evidence_strength", "insufficient"), self._v(item, "confidence"), list(self._v(item, "uncertainty", []) or []), self._v(item, "provenance", {}), self._refs(item)))
        priorities=[]; plans=[]
        for dim in dimensions:
            if dim.direction == "degrading" or dim.relative_position == "lagging": priority, severity, rationale = "high", "high", "This dimension is weak or degrading relative to the organization's available dimensions."
            elif dim.status == "insufficient_data": priority, severity, rationale = "insufficient_data", "low", "Evidence is insufficient to establish a reliable improvement priority."
            else: continue
            pid=stable_improvement_id(tenant_id, dim.dimension_id, "priority")
            p=ImprovementPriority(pid,tenant_id,dim.dimension_id,dim.dimension_name,priority,severity,rationale,dim.current_score_or_state,dim.previous_score_or_state,dim.direction,"persistent_weakness" if dim.direction=="degrading" else "insufficient_history",dim.evidence_strength,dim.confidence,dim.uncertainty,dim.contributing_references)
            priorities.append(p)
            plans.append(ImprovementPlan(stable_improvement_id(tenant_id,dim.dimension_id,"plan"),tenant_id,dim.dimension_id,dim.dimension_name,"Improve evidence-backed maturity in this dimension.",priority,rationale,dim.contributing_references,"Review the underlying investigation-learning evidence and feedback coverage.","Movement from weakness toward stable or improving maturity.",["future maturity observations show improved direction","reduced persistence of the identified weakness","stronger evidence coverage"],dim.confidence,dim.uncertainty,{"source":"maturity_improvement","upstream":["organizational_maturity","maturity_reporting"],"tenant_id":tenant_id},dim.contributing_references))
        priorities.sort(key=lambda x:(PRIORITY.get(x.priority,99),-float(x.confidence or 0),x.priority_id)); plans.sort(key=lambda x:(PRIORITY.get(x.priority,99),x.plan_id))
        strongest=dimensions[0].dimension_name if dimensions else None; weakest=dimensions[-1].dimension_name if dimensions else None
        summary={"classification":"improvement_required" if priorities else "generally_healthy","strongest_dimension":strongest,"weakest_dimension":weakest,"historical_direction":self._v(report,"trajectory","insufficient_data"),"confidence":self._v(report,"confidence"),"evidence_strength":self._v(report,"evidence_strength","insufficient"),"uncertainty":self._v(report,"uncertainty",[])}
        return {"tenant_id":tenant_id,"current_maturity":maturity.to_dict() if hasattr(maturity,"to_dict") else (maturity or {}),"comparative_dimensions":[x.to_dict() for x in dimensions],"priority_signals":[x.to_dict() for x in priorities],"improvement_plans":[x.to_dict() for x in plans],"executive_summary":summary,"confidence":self._v(report,"confidence"),"evidence_strength":self._v(report,"evidence_strength","insufficient"),"uncertainty":self._v(report,"uncertainty",[]),"provenance":self._v(report,"provenance",{}),"contributing_references":self._v(report,"contributing_references",[]),"advisory_only":True}
