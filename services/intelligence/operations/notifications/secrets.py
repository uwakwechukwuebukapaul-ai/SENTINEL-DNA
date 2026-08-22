"""Provider-neutral secret references; values never enter operational persistence."""
from __future__ import annotations

import os


class SecretResolver:
    def resolve(self, secret_reference: str) -> str:
        raise NotImplementedError


class EnvironmentSecretResolver(SecretResolver):
    """Resolve only env:// references, preserving a replaceable secret boundary."""

    def resolve(self, secret_reference: str) -> str:
        reference = str(secret_reference or "")
        if not reference.startswith("env://"):
            raise ValueError("unsupported_secret_reference")
        name = reference[6:]
        if not name or not name.replace("_", "").isalnum():
            raise ValueError("invalid_secret_reference")
        value = os.environ.get(name)
        if not value:
            raise ValueError("secret_unavailable")
        return value
