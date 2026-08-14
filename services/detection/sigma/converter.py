class SigmaConverter:
    LEVELS = {"low": "LOW", "medium": "MEDIUM", "high": "HIGH", "critical": "CRITICAL"}
    def to_detection_metadata(self, document): return {"name": document.get("title", ""), "description": document.get("description", ""), "severity": self.LEVELS.get(str(document.get("level", "medium")).lower(), "MEDIUM"), "mitre_techniques": [tag.split(".")[-1] for tag in document.get("tags", []) if str(tag).startswith("attack.t")], "query_logic": str(document.get("detection", {})), "data_source": "Telemetry"}
