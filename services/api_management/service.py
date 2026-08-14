import hashlib, secrets
from datetime import datetime, timezone
class APIManagementService:
    def __init__(self): self.keys = {}; self.usage = []
    def create_key(self, organization_id, name):
        raw = secrets.token_urlsafe(32); key = {"id": secrets.token_hex(8), "organization_id": organization_id, "name": name, "prefix": raw[:8], "hash": hashlib.sha256(raw.encode()).hexdigest(), "created_at": datetime.now(timezone.utc).isoformat()}; self.keys[key["id"]] = key; return {**{k: v for k, v in key.items() if k != "hash"}, "secret": raw}
    def authenticate(self, raw):
        digest = hashlib.sha256(raw.encode()).hexdigest(); return next((x for x in self.keys.values() if x["hash"] == digest), None)
    def track(self, organization_id, endpoint): self.usage.append({"organization_id": organization_id, "endpoint": endpoint, "timestamp": datetime.now(timezone.utc).isoformat()})
    def list(self, organization_id): return [{k: v for k, v in x.items() if k != "hash"} for x in self.keys.values() if x["organization_id"] == organization_id]
