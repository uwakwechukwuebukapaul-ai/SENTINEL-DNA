from __future__ import annotations
from typing import Any
from .base import AIProvider
from .models import AIResponse

class DeterministicMockProvider(AIProvider):
    """Offline provider for tests and synthetic demonstrations."""
    name = "deterministic_mock"
    offline_only = True

    def generate(self, prompt: str, context: dict[str, Any] | None = None) -> AIResponse:
        context = context or {}
        case_id = str(context.get("case_id", "unknown"))
        evidence = [str(item) for item in context.get("evidence_references", [])]
        return AIResponse(
            content=f"Deterministic analysis for {case_id}: {str(prompt).strip()}",
            confidence=0.75 if prompt and case_id != "unknown" else 0.5,
            evidence_references=evidence,
            metadata={"provider": self.name, "offline_only": True, "synthetic": True},
        )
