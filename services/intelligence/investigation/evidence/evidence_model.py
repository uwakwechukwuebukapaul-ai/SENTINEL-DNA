"""
Sentinel DNA Evidence Model

Normalized investigation evidence object.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Evidence:

    evidence_type: str

    source: str

    value: Any

    confidence: float = 0.0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    created_at: str = field(
        default_factory=lambda:
            datetime.now(
                timezone.utc
            ).isoformat()
    )


    def to_dict(self):

        return {
            "type": self.evidence_type,
            "source": self.source,
            "value": self.value,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }