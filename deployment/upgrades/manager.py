class UpgradeManager:
    def __init__(self, version="1.0.0"): self.version = version; self.history = []
    def plan(self, target_version, migrations): return {"from": self.version, "to": target_version, "migrations": migrations, "rollback_ready": True}
    def apply(self, target_version, migrations):
        plan = self.plan(target_version, migrations); self.history.append({**plan, "status": "applied"}); self.version = target_version; return self.history[-1]
    def rollback(self):
        if not self.history: return {"status": "nothing_to_rollback"}
        item = self.history[-1]; item["status"] = "rollback_ready"; return item
