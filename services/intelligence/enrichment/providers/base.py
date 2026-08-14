from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from ..models import EnrichmentResult, Indicator

class EnrichmentProvider(ABC):
    name = "provider"

    @abstractmethod
    def lookup(self, indicator: Indicator) -> dict[str, Any] | None: ...

    @abstractmethod
    def enrich(self, indicator: Indicator) -> EnrichmentResult: ...
