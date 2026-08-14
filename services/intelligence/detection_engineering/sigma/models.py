from dataclasses import asdict, dataclass, field
from typing import Any
@dataclass
class SigmaMetadata:
    category: str=""; product: str=""; service: str=""; datasource: str=""
    def to_dict(self): return asdict(self)
@dataclass
class SigmaRule:
    rule_id: str; title: str; description: str=""; author: str="synthetic"; status: str="stable"; log_source: SigmaMetadata=field(default_factory=SigmaMetadata); detection_logic: dict[str,Any]=field(default_factory=dict); severity: str="medium"; tags: list[str]=field(default_factory=list); mitre_techniques: list[str]=field(default_factory=list); references: list[str]=field(default_factory=list); created_at: str=""; synthetic_only: bool=True
    def to_dict(self):
        d=asdict(self); d["log_source"]=self.log_source.to_dict(); return d
