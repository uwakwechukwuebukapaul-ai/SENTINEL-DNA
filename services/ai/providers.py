from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
class AIProvider(ABC):
    name = "generic"
    @abstractmethod
    def generate(self, prompt: str, context: list[dict[str, Any]] | None = None) -> str: ...
    def analyze(self, prompt, context=None): return self.generate(prompt, context)
    def summarize(self, text, context=None): return self.generate(f"Summarize: {text}", context)
    def classify(self, text, labels, context=None): return {"label": labels[0] if labels else "unknown", "provider": self.name}
class SafeProvider(AIProvider):
    def generate(self, prompt, context=None): return f"[{self.name}] Analysis prepared from {len(context or [])} tenant-scoped context items."
class OpenAIProvider(SafeProvider): name = "openai"
class AzureOpenAIProvider(SafeProvider): name = "azure_openai"
class LocalLLMProvider(SafeProvider): name = "local_llm"
class OllamaProvider(SafeProvider): name = "ollama"
