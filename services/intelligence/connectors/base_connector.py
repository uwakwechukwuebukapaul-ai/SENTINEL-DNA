"""
Sentinel DNA Base Connector.

Defines standard interface for
security integrations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any



class BaseConnector(ABC):
    """
    Enterprise connector contract.
    """


    name: str = "base"



    @abstractmethod
    def execute(
        self,
        action: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute connector action.
        """

        raise NotImplementedError