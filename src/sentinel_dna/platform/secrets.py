"""Secret lookup boundary; secret values are never logged or serialized."""
from __future__ import annotations
import os
from typing import Protocol

class SecretProvider(Protocol):
    def get(self, name: str) -> str: ...

class EnvironmentSecretProvider:
    def get(self, name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise KeyError(f"secret {name} is not configured")
        return value
