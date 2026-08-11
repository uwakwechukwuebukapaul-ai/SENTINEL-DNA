from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class InvestigationResult:
    plan_name: str
    results: dict[str, Any]
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
