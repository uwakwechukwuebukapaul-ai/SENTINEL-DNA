from .quality_trends import AnalystQualityTrend

class AnalystQualityTrendService:
    """Read-only aggregation over the existing feedback service/repository."""
    def __init__(self, feedback_service=None): self.feedback_service=feedback_service
    def trend(self, tenant_id):
        feedback=self.feedback_service.list_feedback(tenant_id) if self.feedback_service else []
        feedback=sorted(feedback,key=lambda x:(x.investigation_id,x.created_at,x.feedback_id))
        investigation_ids=sorted({x.investigation_id for x in feedback}); qualities=[]
        for iid in investigation_ids:
            quality=self.feedback_service.quality(tenant_id,iid)
            if quality: qualities.append((iid,quality))
        agreements=sum(x.outcome_agreement=="agree" for x in feedback); disagreements=sum(x.outcome_agreement=="disagree" for x in feedback)
        unresolved=sum(bool(q.uncertainty or q.status in {"needs_review","insufficient_data"}) for _,q in qualities)
        human=sum(bool(q.advisory_only) for _,q in qualities)
        insufficient=sum(x.evidence_sufficiency in {"insufficient","partially_sufficient"} for x in feedback)
        confidences=[x.confidence for x in feedback if x.confidence is not None]
        uncertainty=sorted({u for _,q in qualities for u in q.uncertainty})
        if not feedback: direction="insufficient_data"
        elif disagreements or unresolved: direction="needs_review"
        elif agreements==len(feedback): direction="stable"
        else: direction="mixed"
        provenance={"source":"investigation_feedback","feedback_count":len(feedback),"quality_signal_count":len(qualities)}
        return AnalystQualityTrend(tenant_id,len(investigation_ids),len(feedback),len(qualities),agreements,disagreements,unresolved,human,insufficient,sum(confidences)/len(confidences) if confidences else None,uncertainty,direction,provenance,[x.feedback_id for x in feedback],investigation_ids,sorted({x.outcome_reference for x in feedback if x.outcome_reference}))
