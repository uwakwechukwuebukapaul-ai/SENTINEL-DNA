class CommandAggregator:
    def aggregate(self, tenant_id, sources=None):
        sources = sources or {}
        availability = dict(sources.get("subsystem_availability", {}))
        for name, value in sources.items():
            if name != "subsystem_availability": availability.setdefault(name, "AVAILABLE" if value is not None else "UNAVAILABLE")
        return {"tenant_id": tenant_id, "platform_health": sources.get("platform_health", {}),
                "active_investigations": list(sources.get("investigations", [])),
                "critical_findings": list(sources.get("critical_findings", [])),
                "subsystem_availability": availability,
                "uncertainty": "UNKNOWN" if any(v != "AVAILABLE" for v in availability.values()) else ""}
