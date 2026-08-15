class ContextNormalizer:
    def build(self, tenant_id, sources=None):
        sources = sources or {}
        result={k:list(sources.get(k, [])) if isinstance(sources.get(k, []), (list,tuple)) else sources.get(k, {})
                for k in ("investigations","evidence","risk","compliance","governance","operations","lifecycle","decisions")}
        availability=dict(sources.get("subsystem_availability", {}))
        for key in result: availability.setdefault(key, "AVAILABLE" if key in sources else "UNAVAILABLE")
        result["subsystem_availability"]=availability
        result["uncertainty"]="UNKNOWN" if any(v != "AVAILABLE" for v in availability.values()) else ""
        return result
