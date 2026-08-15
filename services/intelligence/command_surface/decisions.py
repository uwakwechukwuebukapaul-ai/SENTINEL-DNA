from .models import DecisionItem

class DecisionBuilder:
    def build(self, tenant_id, records=None):
        result=[]
        for x in records or []:
            evidence=list(x.get("evidence_references", x.get("supporting_evidence", [])))
            confidence=x.get("confidence"); unknown=confidence is None or not evidence
            result.append(DecisionItem(tenant_id, str(x.get("category", "EXECUTIVE")).upper(), x.get("title", "Review decision"),
                x.get("current_state", "UNKNOWN"), x.get("recommended_next_review_step", "Review source context"), evidence,
                confidence, "UNKNOWN" if unknown else x.get("uncertainty", ""), dict(x.get("provenance", {})),
                bool(x.get("approval_required", False)), x.get("lifecycle_state", "UNKNOWN"), str(x.get("source_reference", x.get("id", "")))))
        return result
