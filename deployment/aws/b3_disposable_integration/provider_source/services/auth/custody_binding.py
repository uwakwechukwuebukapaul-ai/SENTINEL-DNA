"""Strict disposable-provider custody binding normalization."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any, Mapping

PROTOCOL_VERSION = "sentinel-dna-replay-custody-v1"
BINDING_FIELDS = (
    "protocol_version", "initialization_id", "activation_id", "principal_id", "role",
    "control_tenant_id", "environment", "database_target_identity", "release_commit",
    "release_tree", "release_image_digest", "release_binding_manifest_hash",
    "tenant_authorization_hash", "challenge_hash", "purpose", "created_at", "expires_at",
)
EMPTY_SCOPE_VALUE = "NOT_APPLICABLE"


class CustodyBindingError(ValueError):
    pass


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value):
        raise CustodyBindingError(f"{field}_timestamp_invalid")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)
    except ValueError as exc:
        raise CustodyBindingError(f"{field}_timestamp_invalid") from exc


def normalize_custody_binding(binding: Mapping[str, Any], *, now: datetime | None = None, allow_expired: bool = False) -> dict[str, str]:
    values = dict(binding)
    values.setdefault("protocol_version", PROTOCOL_VERSION)
    if set(values) != set(BINDING_FIELDS):
        raise CustodyBindingError("custody_binding_fields_invalid")
    if any(not isinstance(values[field], str) or not values[field] for field in BINDING_FIELDS):
        raise CustodyBindingError("custody_binding_required_field_missing")
    if values["protocol_version"] != PROTOCOL_VERSION:
        raise CustodyBindingError("custody_protocol_version_invalid")
    created, expires = _timestamp(values["created_at"], "created_at"), _timestamp(values["expires_at"], "expires_at")
    if expires <= created:
        raise CustodyBindingError("custody_timestamp_interval_invalid")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if created > current + timedelta(seconds=5):
        raise CustodyBindingError("created_at_clock_skew_exceeded")
    if not allow_expired and expires <= current:
        raise CustodyBindingError("custody_reservation_expired")
    return {field: values[field] for field in BINDING_FIELDS}


def binding_hash(binding: Mapping[str, Any], *, now: datetime | None = None, allow_expired: bool = False) -> str:
    return hashlib.sha256(canonical_json(normalize_custody_binding(binding, now=now, allow_expired=allow_expired))).hexdigest()
