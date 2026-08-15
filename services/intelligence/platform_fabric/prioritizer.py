class PlatformPrioritizer:
    weights={"critical":4,"high":3,"medium":2,"low":1}
    def priority(self,record):
        score=self.weights.get(record.severity,1)+(1 if record.requires_human_review else 0)+(1 if record.data.get("business_impact") in {"high","critical"} else 0)
        return "critical" if score>=6 else "high" if score>=4 else "medium" if score>=2 else "low"
    def rationale(self,record,priority): return f"Cross-domain attention is advisory: {record.source_subsystem} reported {record.entity_type} {record.source_record_id} with severity {record.severity}; unified priority is {priority} from deterministic severity, review, and business-impact signals."
