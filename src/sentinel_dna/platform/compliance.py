"""Tenant-isolated audit export, retention policy, and activity reporting."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from sentinel_dna.saas.usage import UsageMeter
from sentinel_dna.saas.identity import validate_identifier

@dataclass(frozen=True)
class RetentionPolicy:
    audit_days: int = 365; security_event_days: int = 365
    def cutoff(self, kind: str) -> str:
        days=self.audit_days if kind=="audit" else self.security_event_days
        return (datetime.now(timezone.utc)-timedelta(days=days)).isoformat()

class ComplianceService:
    def __init__(self, data_dir="data") -> None: self.data_dir=Path(data_dir); self.usage=UsageMeter(str(data_dir))
    def export_audit(self, tenant_id: str) -> list[dict]:
        tenant_id=validate_identifier(tenant_id,"org")
        return [event.__dict__ for event in self.usage.get_usage(tenant_id)]
    def tenant_activity_report(self, tenant_id: str) -> dict:
        tenant_id=validate_identifier(tenant_id,"org")
        events=self.export_audit(tenant_id)
        return {"tenant_id":tenant_id,"event_count":len(events),"usage_totals":self.usage.aggregate_usage(tenant_id)}
    def archive_security_event(self, tenant_id: str, event_type: str, metadata: dict) -> None:
        self.usage.record_event(tenant_id,event_type,metadata=metadata)
