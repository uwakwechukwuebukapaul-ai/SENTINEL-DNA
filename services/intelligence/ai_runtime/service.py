"""Governed AI reasoning adapter for investigation intelligence."""

from __future__ import annotations

import json
import os
from typing import Any

from .base import AIProvider
from .mock import DeterministicMockProvider
from .models import AIResponse


class AIRuntimeService:
    """Build bounded prompts and request reasoning without executing actions."""

    _PROVIDERS = {"mock": DeterministicMockProvider}
    _FUTURE_PROVIDERS = {"openai", "azure", "local"}

    def __init__(self, provider: AIProvider | None = None) -> None:
        self.provider = provider

    @classmethod
    def from_environment(cls) -> "AIRuntimeService | None":
        provider_name = os.getenv("AI_PROVIDER", "").strip().lower()
        if not provider_name:
            return None
        provider_type = cls._PROVIDERS.get(provider_name)
        if provider_type is None and provider_name in cls._FUTURE_PROVIDERS:
            # Recognize reserved provider names without attempting external calls.
            return None
        if provider_type is None:
            raise ValueError(f"Unsupported AI_PROVIDER: {provider_name}")
        return cls(provider_type())

    def reason(self, context: Any) -> AIResponse:
        if self.provider is None:
            raise RuntimeError("AI runtime provider is not configured")

        snapshot = self._snapshot(context)
        prompt = self._build_prompt(snapshot)
        response = self.provider.generate(prompt, {
            "case_id": snapshot["case_id"],
            "evidence_references": snapshot["evidence_references"],
        })
        # Providers are advisory only; preserve explicit offline/synthetic markers.
        metadata = {
            "ai_runtime": True,
            "actions_executed": False,
            "evidence_modified": False,
            "synthetic": bool(response.metadata.get("synthetic", False)),
            "offline_only": bool(response.metadata.get("offline_only", False)),
            **response.metadata,
        }
        return AIResponse(
            content=response.content,
            confidence=response.confidence,
            evidence_references=list(response.evidence_references),
            metadata=metadata,
        )

    def _snapshot(self, context: Any) -> dict[str, Any]:
        if hasattr(context, "snapshot"):
            data = context.snapshot()
        elif hasattr(context, "to_dict"):
            data = context.to_dict()
        else:
            data = vars(context)
        data = dict(data)
        evidence = data.get("evidence", []) or []
        references = [
            str(item.get("id") or item.get("reference") or index)
            if isinstance(item, dict) else str(index)
            for index, item in enumerate(evidence)
        ]
        return {
            "case_id": str(data.get("case_id") or data.get("investigation_id") or "unknown"),
            "alert": data.get("alert", {}),
            "evidence": evidence,
            "iocs": data.get("iocs", []),
            "timeline": data.get("timeline", []),
            "evidence_references": references,
        }

    @staticmethod
    def _build_prompt(snapshot: dict[str, Any]) -> str:
        return "Review this investigation context. Explain observed risk and uncertainty. Do not execute actions or alter evidence.\n" + json.dumps(
            {key: snapshot[key] for key in ("case_id", "alert", "evidence", "iocs", "timeline")},
            sort_keys=True,
            default=str,
        )
