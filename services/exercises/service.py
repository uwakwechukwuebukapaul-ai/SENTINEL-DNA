from datetime import datetime, timezone
from uuid import uuid4
class ExerciseService:
    def __init__(self): self.items = {}
    def create(self, organization_id, name, scenario):
        item = {"id": str(uuid4()), "organization_id": organization_id, "name": name, "scenario": scenario, "status": "created", "detections": [], "investigations": [], "responses": [], "score": None, "created_at": datetime.now(timezone.utc).isoformat()}; self.items[item["id"]] = item; return item
    def execute(self, exercise_id, organization_id, detection=None, investigation=None, response=None):
        item = self.items.get(exercise_id)
        if not item or item["organization_id"] != organization_id: raise LookupError("exercise_not_found")
        item["status"] = "completed"; item["detections"] = detection or []; item["investigations"] = investigation or []; item["responses"] = response or []; item["score"] = self.score(item); return item
    def score(self, item):
        dimensions = {"detection_validation": bool(item["detections"]), "investigation_validation": bool(item["investigations"]), "response_validation": bool(item["responses"])}; return {"dimensions": dimensions, "overall": round(sum(dimensions.values()) / len(dimensions) * 100, 2)}
    def list(self, organization_id): return [x for x in self.items.values() if x["organization_id"] == organization_id]
