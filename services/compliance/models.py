from dataclasses import asdict, dataclass, field
from typing import Any
@dataclass
class ComplianceFramework:
    framework_id:str; name:str; version:str="1.0"; description:str=""
    def to_dict(self): return asdict(self)
@dataclass
class SecurityControl:
    control_id:str; framework_id:str; name:str; description:str=""; category:str=""; requirements:list[str]=field(default_factory=list)
    def to_dict(self): return asdict(self)
@dataclass
class ControlAssessment:
    assessment_id:str; tenant_id:str; control_id:str; status:str="unknown"; score:float=0.0; evidence_refs:list[str]=field(default_factory=list); evaluated_at:str=""
    def to_dict(self): return asdict(self)
@dataclass
class RiskFinding:
    finding_id:str; tenant_id:str; category:str; severity:str; description:str; evidence_refs:list[str]=field(default_factory=list); mitigation:str=""
    def to_dict(self): return asdict(self)
@dataclass
class SecurityRiskScore:
    tenant_id:str; score:int; severity:str; contributing_factors:list[str]=field(default_factory=list); recommendations:list[str]=field(default_factory=list)
    def to_dict(self): return asdict(self)
