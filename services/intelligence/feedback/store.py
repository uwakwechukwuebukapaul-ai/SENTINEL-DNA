from datetime import datetime, timezone
from uuid import uuid4
class FeedbackStore:
    def __init__(self): self.records = []
    def record(self, organization_id, user_id, decision_id, outcome, correction=None, confidence=None):
        if not organization_id: raise ValueError("organization_required")
        item = {"id": str(uuid4()), "organization_id": organization_id, "user_id": user_id, "decision_id": decision_id, "outcome": outcome, "correction": correction, "confidence": confidence, "created_at": datetime.now(timezone.utc).isoformat()}; self.records.append(item); return item
    def list(self, organization_id): return [item for item in self.records if item["organization_id"] == organization_id]
    def metrics(self, organization_id):
        records = self.list(organization_id); total = len(records); accepted = sum(x["outcome"] == "approved" for x in records); rejected = sum(x["outcome"] == "rejected" for x in records); corrections = sum(bool(x["correction"]) for x in records)
        return {"feedback_count": total, "accepted_recommendations": accepted, "rejected_recommendations": rejected, "analyst_corrections": corrections, "confidence_accuracy": round(accepted / total * 100, 2) if total else 0}
