"""Provider-neutral deterministic similarity boundary for organizational memory."""
from __future__ import annotations

from abc import ABC, abstractmethod
import re
from typing import Any, Iterable


def memory_tokens(values: Iterable[Any]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        if value is None:
            continue
        tokens.update(token.lower() for token in re.findall(r"[a-zA-Z0-9_.:-]+", str(value)) if len(token) > 1)
    return tokens


class MemorySimilarityProvider(ABC):
    """Extension point for future vector/embedding providers."""

    provider_name = "provider-neutral"

    @abstractmethod
    def similarity(self, query: Iterable[Any], candidate: Iterable[Any]) -> float:
        raise NotImplementedError

    def rank(self, query: Iterable[Any], candidates: Iterable[tuple[str, Iterable[Any]]]) -> list[dict[str, Any]]:
        scored = [
            {"record_id": str(record_id), "score": self.similarity(query, values)}
            for record_id, values in candidates
        ]
        scored.sort(key=lambda item: (-item["score"], item["record_id"]))
        return scored


class DeterministicSimilarityProvider(MemorySimilarityProvider):
    """Set-based baseline; no embeddings, model calls, or external state."""

    provider_name = "deterministic-jaccard-v1"

    def similarity(self, query: Iterable[Any], candidate: Iterable[Any]) -> float:
        left, right = memory_tokens(query), memory_tokens(candidate)
        if not left and not right:
            return 1.0
        if not left or not right:
            return 0.0
        return round(len(left & right) / len(left | right), 6)


__all__ = ["DeterministicSimilarityProvider", "MemorySimilarityProvider", "memory_tokens"]
