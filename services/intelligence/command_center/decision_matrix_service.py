"""Deterministic, bounded, read-only multi-scenario comparison."""
from .decision_matrix import DecisionMatrix, ScenarioComparison, stable_matrix_id

class DecisionMatrixService:
    MAX_SCENARIOS=5
    def __init__(self, scenario_service): self.scenario_service=scenario_service
    def evaluate(self, tenant_id, selections):
        if not isinstance(selections,list) or not selections: raise ValueError("empty_scenarios")
        if len(selections)>self.MAX_SCENARIOS: raise ValueError("too_many_scenarios")
        canonical=[]; seen=set()
        for s in selections:
            if not isinstance(s,dict): raise ValueError("invalid_scenario")
            key=(s.get("scenario_type"),s.get("target_dimension"))
            if key in seen: raise ValueError("duplicate_scenario")
            seen.add(key); options=self.scenario_service.options(tenant_id); supported=next((x for x in options["scenarios"] if x["scenario_type"]==key[0] and (not key[1] or key[1] in x.get("target_dimensions",[]))),None)
            if not supported: raise ValueError("unsupported_scenario")
            canonical.append({"scenario_type":key[0],"target_dimension":key[1],"assumption":supported["assumption"]})
        rows=[]
        for s in canonical:
            x=self.scenario_service.evaluate(tenant_id,s); uncertainty=tuple(x.get("uncertainty",[])); trade=[]
            if x.get("score_delta") is not None and x.get("confidence") in ("low","insufficient"): trade.append("improvement_vs_confidence")
            if uncertainty: trade.append("improvement_vs_uncertainty")
            rows.append(ScenarioComparison(tenant_id,stable_matrix_id(tenant_id,canonical),x["scenario_id"],x["scenario_type"],x["title"],x["strategic_area"],x["target_dimension"],x["classification"],x["baseline_score"],x["scenario_score"],x["score_delta"],"high" if x["classification"]=="favorable" else "medium",x["confidence"],x["evidence_strength"],uncertainty,x["provenance"],tuple(x.get("contributing_references",[])),x["expected_focus"],tuple(trade)))
        rank={"high":0,"medium":1,"low":2}; evidence={"strong":0,"high":0,"moderate":1,"medium":1,"limited":2,"insufficient":3}; cls={"favorable":0,"neutral":1,"mixed":2,"unfavorable":3,"not_measurable":4,"insufficient_evidence":5}
        ordered=sorted(rows,key=lambda x:(rank.get(x.strategic_priority,9),cls.get(x.classification,9),evidence.get(x.evidence_strength,9),{"high":0,"medium":1,"low":2,"insufficient":3}.get(x.confidence,9),-(x.score_delta or -999),len(x.uncertainty),x.scenario_id))
        common=sorted({u for x in rows for u in x.uncertainty}); measurable=sum(x.score_delta is not None for x in rows); insufficient=sum(x.classification in ("insufficient_evidence","not_measurable") for x in rows); weakest=max((x.confidence for x in rows),default="insufficient")
        rec={"preferred_focus":ordered[0].title if ordered else "Unavailable","rationale":"The leading scenario presents the strongest currently observed strategic profile; this comparison is hypothetical and does not establish causation.","evidence_strength":ordered[0].evidence_strength if ordered else "insufficient","confidence":ordered[0].confidence if ordered else "insufficient","uncertainty":list(ordered[0].uncertainty) if ordered else ["insufficient_observations"],"alternatives":[x.title for x in ordered[1:]],"advisory_only":True}
        return DecisionMatrix(tenant_id,stable_matrix_id(tenant_id,canonical),{"posture":self.scenario_service._base(tenant_id).get("posture",{})},tuple(x.to_dict() for x in rows),tuple(x.scenario_id for x in ordered),rec,{"trade_offs":sorted({t for x in rows for t in x.trade_offs}),"comparability":"directly_comparable" if len({x.baseline_score is not None for x in rows})==1 else "partially_comparable"},{"total_scenarios":len(rows),"measurable_scenarios":measurable,"insufficient_evidence":insufficient,"strongest_evidence":ordered[0].scenario_id if ordered else None,"common_uncertainty":common},"insufficient" if insufficient==len(rows) else "medium","insufficient" if not rows else ordered[0].evidence_strength,tuple(common+["comparison_uncertainty"] if len({x.target_dimension for x in rows})>1 else common),("strategic_scenario", "executive_strategy"),True).to_dict()
