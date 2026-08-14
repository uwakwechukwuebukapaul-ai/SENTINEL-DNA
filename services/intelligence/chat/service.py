from datetime import datetime, timezone
from services.ai import ReasoningFabric
class AnalystChatService:
    def __init__(self, fabric=None): self.fabric = fabric or ReasoningFabric(); self.conversations = {}
    def ask(self, organization_id, user_id, question, investigation=None):
        result = self.fabric.investigate(organization_id, question, (investigation or {}).get("evidence", [])); item = {"question": question, "answer": result, "user_id": user_id, "created_at": datetime.now(timezone.utc).isoformat()}; self.conversations.setdefault(organization_id, []).append(item); return item
    def history(self, organization_id): return self.conversations.get(organization_id, [])
    def replay(self, investigation):
        events = investigation.get("timeline", []) if isinstance(investigation, dict) else []
        return events or [{"stage": stage, "status": "recorded"} for stage in ("alert_creation", "evidence_collection", "ioc_analysis", "mitre_mapping", "ai_reasoning", "final_decision")]
