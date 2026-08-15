from datetime import datetime, timezone
class RuntimeTelemetry:
    def __init__(self): self.records = []
    def record(self, execution, **details):
        item = {"execution_id": execution.execution_id, "tenant_id": execution.tenant_id, "timestamp": datetime.now(timezone.utc).isoformat(), **details}; self.records.append(item); return item
