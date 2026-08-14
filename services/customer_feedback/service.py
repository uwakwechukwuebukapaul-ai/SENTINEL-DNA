from datetime import datetime, timezone
class CustomerFeedbackService:
    TYPES = {"analyst_feedback", "investigation_quality", "ai_accuracy", "usability_issue", "feature_request"}
    def __init__(self): self.items = []
    def record(self, organization_id, kind, value, user_id=None):
        if kind not in self.TYPES: raise ValueError("invalid_feedback_type")
        item = {"organization_id": organization_id, "kind": kind, "value": value, "user_id": user_id, "created_at": datetime.now(timezone.utc).isoformat()}; self.items.append(item); return item
