"""Canonical JSON and immutable-value helpers for Investigator V1 integrity."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Any


class CanonicalizationError(ValueError):
    """Raised when a value cannot be represented deterministically."""


def freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        values = [freeze(item) for item in value]
        return tuple(sorted(values, key=canonical_json))
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise CanonicalizationError("value is not deterministically serializable")


def thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        thaw(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def sha256_digest(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()
