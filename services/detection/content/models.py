from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from uuid import uuid4
def now(): return datetime.now(timezone.utc).isoformat()
STATUSES = {"DRAFT", "TESTING", "APPROVED", "ACTIVE", "DISABLED", "ARCHIVED"}
@dataclass
class DetectionRule:
    organization_id: str; name: str; description: str; severity: str; author_id: int | None; query_logic: str; data_source: str; mitre_techniques: list[str] = field(default_factory=list); tags: list[str] = field(default_factory=list); status: str = "DRAFT"; version: int = 1; id: str = field(default_factory=lambda: str(uuid4())); created_at: str = field(default_factory=now); updated_at: str = field(default_factory=now)
    def public(self): return asdict(self)
@dataclass
class DetectionRuleVersion:
    rule_id: str; version_number: int; changes: dict; author_id: int | None; created_at: str = field(default_factory=now)
    def public(self): return asdict(self)
@dataclass
class DetectionPackage:
    organization_id: str; name: str; description: str; rules: list[str]; category: str; version: str = "1.0.0"; id: str = field(default_factory=lambda: str(uuid4()))
    def public(self): return asdict(self)
