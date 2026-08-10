"""
Sentinel DNA AI SOC Copilot.

Provides analyst-facing intelligence over
investigation and decision outputs.
"""

from .engine import (
    AISocCopilot,
)

from .models import (
    CopilotResponse,
)

__all__ = [
    "AISocCopilot",
    "CopilotResponse",
]