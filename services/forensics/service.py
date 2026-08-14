import hashlib, json
from datetime import datetime, timezone
from uuid import uuid4
class ForensicsService:
    def __init__(self): self.evidence = {}; self.custody = []
    def add_evidence(self, organization_id, investigation_id, payload, actor_id):
        raw = json.dumps(payload, sort_keys=True, default=str).encode(); item = {"id": str(uuid4()), "organization_id": organization_id, "investigation_id": investigation_id, "sha256": hashlib.sha256(raw).hexdigest(), "payload": payload, "created_at": datetime.now(timezone.utc).isoformat()}; self.evidence[item["id"]] = item; self.custody.append({"evidence_id": item["id"], "actor_id": actor_id, "action": "created", "timestamp": item["created_at"]}); return item
    def snapshot(self, organization_id, investigation_id): return {"id": str(uuid4()), "organization_id": organization_id, "investigation_id": investigation_id, "evidence": [x for x in self.evidence.values() if x["organization_id"] == organization_id and x["investigation_id"] == investigation_id]}
    def export(self, evidence_id, organization_id):
        item = self.evidence.get(evidence_id)
        if not item or item["organization_id"] != organization_id: raise LookupError("evidence_not_found")
        return {"evidence": item, "chain_of_custody": [x for x in self.custody if x["evidence_id"] == evidence_id]}
