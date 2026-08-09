"""
Base Threat Intelligence Provider.

All intelligence sources must implement
this interface.
"""

from abc import ABC, abstractmethod

from typing import Any


class IntelligenceProvider(ABC):
    """
    Abstract intelligence provider.
    """

    name = "base"

    @abstractmethod
    def lookup(
        self,
        indicator: str,
        indicator_type: str,
    ) -> dict[str, Any]:
        """
        Enrich an indicator.
        """

        raise NotImplementedError