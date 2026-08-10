"""
Evidence data models.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class EvidenceArtifact:
    """
    Represents collected investigation evidence.
    """

    evidence_type: str
    value: str
    source: str

    metadata: dict = field(
        default_factory=dict
    )

    created_at: str = field(
        default_factory=lambda:
        datetime.utcnow().isoformat()
    )


    def to_dict(self):
        return {
            "evidence_type": self.evidence_type,
            "value": self.value,
            "source": self.source,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }