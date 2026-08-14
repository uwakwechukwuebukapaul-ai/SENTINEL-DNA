from dataclasses import dataclass, asdict, field
from typing import Any
from uuid import uuid4
@dataclass
class SigmaRule:
    name: str; event_types: list[str] = field(default_factory=list); keywords: list[str] = field(default_factory=list); technique_id: str = ""; tactic: str = ""; description: str = ""; severity: str = "medium"; id: str = field(default_factory=lambda: str(uuid4()))
    def public(self): return asdict(self)
@dataclass
class Alert:
    rule_id: str; rule_name: str; event: dict[str, Any]; severity: str; technique_id: str; tactic: str; description: str; id: str = field(default_factory=lambda: str(uuid4()))
    def public(self): return asdict(self)
