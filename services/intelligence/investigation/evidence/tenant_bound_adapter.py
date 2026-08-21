"""Tenant-bound evidence normalization for the canonical investigator path."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
import re
from typing import Any


_REFERENCE_KEYS = ("evidence_id", "artifact_id", "reference", "id")
_CASE_KEYS = ("case_id", "investigation_id")
_STATUS_KEYS = ("status", "evidence_status")
_TYPE_KEYS = ("evidence_type", "artifact_type", "type")
_SENSITIVE_KEY_PARTS = (
    "password", "secret", "token", "api_key", "apikey", "authorization",
    "cookie", "credential", "private_key", "access_key", "client_secret",
    "raw_response", "provider_response", "raw_payload", "raw_body",
    "provider_payload", "provider_data", "payload", "response",
)
_PROVENANCE_KEYS = frozenset(
    {
        "source", "source_type", "source_identifier", "collection_method", "provider",
        "provider_name", "provider_id", "provider_version", "provider_record",
        "observation_id", "observation_digest", "observed_at", "captured_at",
        "reference", "integrity_hash",
    }
)
_SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"\b(?:sk|pk|ghp|github_pat|xox[baprs])-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9._-]+\.[A-Za-z0-9._-]+\b"),
)


class TenantBoundEvidenceAdapter:
    """Validate and safely project service evidence for one investigation."""

    def adapt(
        self,
        evidence: Any,
        *,
        case_id: str,
        tenant_id: str | None,
        actor_id: str | None = None,
        correlation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return deterministic, tenant-bound evidence projections.

        Empty input is a no-op for compatibility. Non-empty input is
        fail-closed unless ownership, case scope, provenance, status, and an
        immutable reference are explicit.
        """
        records = self._records(evidence)
        if not records:
            return []
        if not tenant_id:
            raise PermissionError("tenant context is required for evidence")
        if not case_id:
            raise PermissionError("investigation case is required for evidence")

        normalized = [
            self._normalize_record(
                record,
                case_id=str(case_id),
                tenant_id=str(tenant_id),
                actor_id=actor_id,
                correlation_id=correlation_id,
            )
            for record in records
        ]

        by_reference: dict[str, dict[str, Any]] = {}
        for item in normalized:
            reference = item["evidence_id"]
            previous = by_reference.get(reference)
            if previous is not None:
                if self._canonical(previous) != self._canonical(item):
                    raise PermissionError("conflicting evidence reference")
                continue
            by_reference[reference] = item

        return sorted(
            by_reference.values(),
            key=lambda item: (
                item["evidence_id"], item["case_id"], item["source"], item["evidence_type"]
            ),
        )

    def _records(self, evidence: Any) -> list[Any]:
        if evidence is None:
            return []
        if hasattr(evidence, "artifacts"):
            return list(getattr(evidence, "artifacts") or [])
        if isinstance(evidence, Mapping) and "artifacts" in evidence:
            return list(evidence.get("artifacts") or [])
        if isinstance(evidence, (list, tuple, set, frozenset)):
            return list(evidence)
        return [evidence]

    @staticmethod
    def _as_mapping(record: Any) -> dict[str, Any]:
        if isinstance(record, Mapping):
            return dict(record)
        if is_dataclass(record):
            return asdict(record)
        to_dict = getattr(record, "to_dict", None)
        if callable(to_dict):
            value = to_dict()
            if isinstance(value, Mapping):
                return dict(value)
        attributes = {}
        for name in (
            "evidence_id", "artifact_id", "reference", "id", "case_id",
            "investigation_id", "tenant_id", "actor_id", "correlation_id",
            "source", "source_type", "evidence_type", "artifact_type", "type",
            "status", "evidence_status", "provenance", "metadata", "value",
            "description", "summary", "risk", "confidence", "indicators",
        ):
            if hasattr(record, name):
                attributes[name] = getattr(record, name)
        return attributes

    @staticmethod
    def _metadata(record: Mapping[str, Any]) -> dict[str, Any]:
        value = record.get("metadata")
        return dict(value) if isinstance(value, Mapping) else {}

    def _normalize_record(
        self,
        original: Any,
        *,
        case_id: str,
        tenant_id: str,
        actor_id: str | None,
        correlation_id: str | None,
    ) -> dict[str, Any]:
        record = self._as_mapping(original)
        metadata = self._metadata(record)

        if self._first(record, metadata, ("tenant_id",)) != tenant_id:
            raise PermissionError("evidence tenant does not match investigation tenant")

        reference = self._first(record, metadata, _REFERENCE_KEYS)
        reference = self._safe_text(reference)
        if reference is None:
            raise PermissionError("evidence reference is required")

        if self._first(record, metadata, _CASE_KEYS) != case_id:
            raise PermissionError("evidence case does not match investigation case")

        actual_correlation = self._first(record, metadata, ("correlation_id",))
        if correlation_id and actual_correlation and str(actual_correlation) != str(correlation_id):
            raise PermissionError("evidence correlation does not match investigation correlation")

        actual_actor = self._first(record, metadata, ("actor_id",))
        if actual_actor and actor_id and str(actual_actor) != str(actor_id):
            raise PermissionError("evidence actor does not match investigation actor")

        provenance = record.get("provenance")
        if not isinstance(provenance, Mapping):
            provenance = metadata.get("provenance")
        if not isinstance(provenance, Mapping):
            provenance = {}

        source_value = record.get("source")
        if source_value is None or str(source_value).strip().lower() == "unknown":
            source_value = metadata.get("source")
        if source_value is None and isinstance(provenance, Mapping):
            source_value = provenance.get("source")
        source = self._safe_text(source_value)
        if source is None or source.lower() == "unknown":
            raise PermissionError("evidence provenance is required")

        evidence_type = self._safe_text(self._first(record, metadata, _TYPE_KEYS))
        if evidence_type is None:
            raise PermissionError("evidence type is required")

        status = self._safe_text(self._first(record, metadata, _STATUS_KEYS))
        if status is None:
            raise PermissionError("evidence status is required")

        safe_provenance = self._safe_mapping(
            {key: value for key, value in provenance.items() if str(key) in _PROVENANCE_KEYS}
        )
        if not safe_provenance:
            raise PermissionError("evidence provenance is required")

        result: dict[str, Any] = {
            "evidence_id": str(reference),
            "case_id": case_id,
            "tenant_id": tenant_id,
            "source": str(source),
            "evidence_type": str(evidence_type),
            "status": str(status),
            "provenance": safe_provenance,
        }
        source_type = self._safe_text(
            self._first(record, metadata, ("source_type",))
            or safe_provenance.get("source_type")
        )
        if source_type is not None:
            result["source_type"] = source_type
        resolved_actor = actual_actor or actor_id
        resolved_correlation = actual_correlation or correlation_id
        if resolved_actor:
            result["actor_id"] = str(resolved_actor)
        if resolved_correlation:
            result["correlation_id"] = str(resolved_correlation)

        for key in ("description", "summary", "risk", "confidence", "indicators", "created_at", "captured_at"):
            value = self._first(record, metadata, (key,))
            if value is not None:
                safe_value = self._safe_value(value, key=key)
                if safe_value is not None:
                    result[key] = safe_value
        if "value" in record:
            safe_value = self._safe_value(record["value"], key="value")
            if safe_value is not None:
                result["value"] = safe_value

        excluded = {
            "tenant_id", "actor_id", "correlation_id", "case_id", "investigation_id",
            "provenance", "source", "status", "evidence_status", "evidence_id",
            "artifact_id", "reference", "id", "type", "evidence_type", "artifact_type",
        }
        safe_metadata = self._safe_mapping({key: value for key, value in metadata.items() if key not in excluded})
        if safe_metadata:
            result["metadata"] = safe_metadata
        return result

    @staticmethod
    def _first(record: Mapping[str, Any], metadata: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
        for key in keys:
            value = record.get(key)
            if value is not None and value != "":
                return value
        for key in keys:
            value = metadata.get(key)
            if value is not None and value != "":
                return value
        return None

    def _safe_mapping(self, value: Mapping[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key in sorted(value, key=str):
            if self._sensitive_key(key):
                continue
            safe = self._safe_value(value[key], key=str(key))
            if safe is not None:
                result[str(key)] = safe
        return result

    def _safe_value(self, value: Any, *, key: str) -> Any:
        if self._sensitive_key(key):
            return None
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            if any(pattern.search(value) for pattern in _SENSITIVE_VALUE_PATTERNS):
                return None
            return value
        if isinstance(value, Mapping):
            return self._safe_mapping(value)
        if isinstance(value, (list, tuple, set, frozenset)):
            values = [self._safe_value(item, key=key) for item in value]
            return [item for item in values if item is not None]
        return None

    def _safe_text(self, value: Any) -> str | None:
        if value is None:
            return None
        safe = self._safe_value(str(value), key="text")
        if not isinstance(safe, str) or not safe.strip():
            return None
        return safe.strip()

    @staticmethod
    def _sensitive_key(key: Any) -> bool:
        normalized = str(key).lower().replace("-", "_")
        return any(part in normalized for part in _SENSITIVE_KEY_PARTS)

    @staticmethod
    def _canonical(value: Mapping[str, Any]) -> str:
        import json

        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
