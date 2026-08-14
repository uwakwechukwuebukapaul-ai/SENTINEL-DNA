class DetectionRuleValidator:
    SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}; SOURCES = {"Windows Security Logs", "Linux Logs", "Syslog", "Cloud Logs", "Firewall Logs", "Telemetry"}
    def validate(self, data):
        errors = []; warnings = []
        for field in ("name", "description", "query_logic", "data_source"):
            if not data.get(field): errors.append(f"missing_{field}")
        if str(data.get("severity", "")).upper() not in self.SEVERITIES: errors.append("invalid_severity")
        if data.get("data_source") not in self.SOURCES: errors.append("unsupported_data_source")
        for technique in data.get("mitre_techniques", []):
            if not str(technique).startswith("T"): warnings.append(f"unrecognized_mitre:{technique}")
        return {"valid": not errors, "errors": errors, "warnings": warnings}
