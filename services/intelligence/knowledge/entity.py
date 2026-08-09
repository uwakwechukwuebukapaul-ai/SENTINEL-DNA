"""
Sentinel DNA Knowledge Entity Model
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Entity:
    """
    Intelligence graph entity.
    """

    id: str

    entity_type: str

    value: str

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    @property
    def relation_type(self):
        """
        Compatibility field.

        Relationships are represented by the
        Relationship model, but older consumers
        expect entities to expose this attribute.
        """

        return self.entity_type