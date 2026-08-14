from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from .models import AIResponse

class AIProvider(ABC):
    name = "provider"

    @abstractmethod
    def generate(self, prompt: str, context: dict[str, Any] | None = None) -> AIResponse:
        """Generate a governed response from a prompt and bounded context."""
        raise NotImplementedError
