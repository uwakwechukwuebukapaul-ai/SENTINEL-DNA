import json
from abc import ABC, abstractmethod
from typing import Any

from sentinel_dna.telemetry.models import SecurityAlert, TelemetryValidationError


class TelemetryAdapter(ABC):
    @abstractmethod
    def normalize(self, raw_event: Any) -> SecurityAlert:
        raise NotImplementedError


class JSONTelemetryAdapter(TelemetryAdapter):
    entity_fields = ("users", "hosts", "ips", "domains", "hashes")

    def normalize(self, raw_event: Any) -> SecurityAlert:
        event = self._load_event(raw_event)
        alert_id = self._required_text(event, "id", "alert ID")
        title = self._required_text(event, "title", "title")
        return SecurityAlert(
            alert_id=alert_id,
            source=self._optional_text(event, "source", "json"),
            timestamp=self._optional_text(event, "timestamp", ""),
            title=title,
            severity=self._optional_text(event, "severity", "medium").lower(),
            description=self._optional_text(event, "description", ""),
            entities=self._normalize_entities(event.get("entities", {})),
            raw_event=event,
            metadata=self._normalize_metadata(event.get("metadata", {})),
        )

    def _load_event(self, raw_event: Any) -> dict[str, Any]:
        if isinstance(raw_event, str):
            try:
                raw_event = json.loads(raw_event)
            except json.JSONDecodeError as exc:
                raise TelemetryValidationError(f"raw_event must be valid JSON: {exc.msg}") from exc
        if not isinstance(raw_event, dict):
            raise TelemetryValidationError("raw_event must be a dictionary or JSON object string")
        return dict(raw_event)

    def _required_text(self, event: dict[str, Any], key: str, label: str) -> str:
        value = event.get(key)
        if not isinstance(value, str) or not value.strip():
            raise TelemetryValidationError(f"missing required {label}")
        return value.strip()

    def _optional_text(self, event: dict[str, Any], key: str, default: str) -> str:
        value = event.get(key, default)
        if value is None:
            return default
        return str(value).strip() or default

    def _normalize_entities(self, entities: Any) -> dict[str, list[str]]:
        if entities is None:
            entities = {}
        if not isinstance(entities, dict):
            raise TelemetryValidationError("entities must be a dictionary")
        normalized = {}
        for field_name in self.entity_fields:
            values = entities.get(field_name, [])
            if values is None:
                values = []
            if isinstance(values, str):
                values = [values]
            if not isinstance(values, list):
                raise TelemetryValidationError(f"entities.{field_name} must be a list")
            normalized[field_name] = [str(value).strip() for value in values if str(value).strip()]
        return normalized

    def _normalize_metadata(self, metadata: Any) -> dict[str, Any]:
        if metadata is None:
            return {}
        if not isinstance(metadata, dict):
            raise TelemetryValidationError("metadata must be a dictionary")
        return dict(metadata)
