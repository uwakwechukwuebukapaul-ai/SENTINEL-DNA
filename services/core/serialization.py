"""Safe JSON boundary serialization for Sentinel DNA domain values."""
from __future__ import annotations
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

_PRIVATE_KEYS = {"password", "password_hash", "secret", "token", "api_key", "key"}

def serialize(value: Any) -> Any:
    """Return a JSON-safe, acyclic snapshot of a domain value.

    Investigation results cross API, reporting, and persistence boundaries.  A
    boundary snapshot must therefore never retain a domain/runtime object or a
    reference back to an enclosing object.
    """
    return _serialize(value, active=set())


def _serialize(value: Any, *, active: set[int]) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return _serialize(value.value, active=active)
    value_id = id(value)
    if value_id in active:
        return "[circular reference omitted]"
    active.add(value_id)
    try:
        if isinstance(value, (list, tuple, set)):
            return [_serialize(item, active=active) for item in value]
        if isinstance(value, dict):
            return {
                str(k): _serialize(v, active=active)
                for k, v in value.items()
                if not str(k).startswith("_") and str(k).lower() not in _PRIVATE_KEYS
            }
        if is_dataclass(value):
            return {
                field.name: _serialize(getattr(value, field.name), active=active)
                for field in fields(value)
                if not field.name.startswith("_") and field.name.lower() not in _PRIVATE_KEYS
            }
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            return _serialize(to_dict(), active=active)
        return str(value)
    finally:
        active.remove(value_id)

__all__ = ["serialize"]
