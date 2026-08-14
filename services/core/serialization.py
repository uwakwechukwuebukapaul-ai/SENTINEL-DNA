"""Safe JSON boundary serialization for Sentinel DNA domain values."""
from __future__ import annotations
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

_PRIVATE_KEYS = {"password", "password_hash", "secret", "token", "api_key", "key"}

def serialize(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return serialize(value.value)
    if isinstance(value, (list, tuple, set)):
        return [serialize(item) for item in value]
    if isinstance(value, dict):
        return {str(k): serialize(v) for k, v in value.items() if not str(k).startswith("_") and str(k).lower() not in _PRIVATE_KEYS}
    if is_dataclass(value):
        return {
            field.name: serialize(getattr(value, field.name))
            for field in fields(value)
            if not field.name.startswith("_") and field.name.lower() not in _PRIVATE_KEYS
        }
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return serialize(to_dict())
    return str(value)

__all__ = ["serialize"]
