"""
Knowledge Graph Relationship Model

Represents relationships between intelligence entities.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Relationship:
    """
    Represents a graph relationship.

    Example:
        Host -> communicates_with -> IOC
    """

    source: str | None = None
    target: str | None = None
    relation_type: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


    def __post_init__(self):

        if self.source is None:
            self.source = self.metadata.get(
                "source_id"
            )

        if self.target is None:
            self.target = self.metadata.get(
                "target_id"
            )


    @property
    def source_id(self):
        return self.source


    @property
    def target_id(self):
        return self.target


    def to_dict(self):

        return {
            "source": self.source,
            "target": self.target,
            "source_id": self.source,
            "target_id": self.target,
            "relation_type": self.relation_type,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }