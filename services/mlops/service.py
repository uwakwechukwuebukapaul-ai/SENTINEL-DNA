from datetime import datetime, timezone
class MLOpsService:
    def __init__(self): self.models = []; self.prompts = []; self.feedback = []; self.confidence = []
    def register_model(self, name, version, provider):
        item = {"name": name, "version": version, "provider": provider, "registered_at": datetime.now(timezone.utc).isoformat()}; self.models.append(item); return item
    def track_prompt(self, organization_id, model_version, prompt_hash): self.prompts.append({"organization_id": organization_id, "model_version": model_version, "prompt_hash": prompt_hash}); return self.prompts[-1]
    def track_confidence(self, organization_id, confidence): self.confidence.append({"organization_id": organization_id, "confidence": confidence}); return self.confidence[-1]
    def add_feedback(self, organization_id, outcome): self.feedback.append({"organization_id": organization_id, "outcome": outcome}); return self.feedback[-1]
    def metrics(self, organization_id):
        feedback = [x for x in self.feedback if x["organization_id"] == organization_id]; values = [x["confidence"] for x in self.confidence if x["organization_id"] == organization_id]; return {"feedback": len(feedback), "confidence_samples": len(values), "average_confidence": round(sum(values) / len(values), 3) if values else 0}
