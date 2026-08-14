from dataclasses import dataclass
from typing import Any


@dataclass
class CaseAssignment:
    case_id: str
    user_id: int
    assigned_by: int | None
    assigned_at: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()
