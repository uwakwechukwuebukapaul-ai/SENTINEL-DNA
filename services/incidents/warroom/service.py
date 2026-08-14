class WarRoomService:
    def snapshot(self, incident, workflow, collaboration, sla): return {"incident": incident, "workflow": workflow, "collaboration": collaboration, "sla": sla, "ai_assessment": incident.get("ai_assessment", "Review AI investigation results"), "response_progress": incident.get("response", {})}
