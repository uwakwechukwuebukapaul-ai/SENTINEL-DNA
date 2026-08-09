"""
Sentinel DNA Playbook Models.
"""

from dataclasses import dataclass, field
from typing import Any



@dataclass
class PlaybookStep:
    """
    Single automation step.
    """

    name: str

    connector: str

    action: str

    parameters: dict[str, Any] = field(
        default_factory=dict
    )

    requires_approval: bool = False



@dataclass
class Playbook:
    """
    Security automation workflow.
    """

    name: str

    description: str

    steps: list[PlaybookStep]

    enabled: bool = True