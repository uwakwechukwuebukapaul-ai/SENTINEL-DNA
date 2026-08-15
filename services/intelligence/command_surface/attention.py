from .models import AttentionItem

class AttentionEvaluator:
    ranks = {"critical": 5, "high": 4, "medium": 3, "low": 2, "unknown": 1}
    def build(self, tenant_id, records=None):
        result=[]
        for x in records or []:
            severity=str(x.get("severity", "unknown")).lower(); confidence=x.get("confidence")
            review=bool(x.get("requires_human_review", True) or confidence is None or not x.get("evidence_references", []))
            priority="high" if severity in {"critical","high"} or review else "medium"
            result.append(AttentionItem(tenant_id, str(x.get("category", "PLATFORM")).upper(), priority, severity, confidence,
                x.get("title", "Review intelligence item"), x.get("rationale", "Source signal requires analyst review."),
                list(x.get("evidence_references", [])), str(x.get("source_reference", x.get("id", ""))), review,
                x.get("timestamp", ""), dict(x.get("provenance", {}))))
        return sorted(result, key=lambda a:(-self.ranks.get(a.severity,1), -int(a.requires_human_review), a.category, a.source_reference))
