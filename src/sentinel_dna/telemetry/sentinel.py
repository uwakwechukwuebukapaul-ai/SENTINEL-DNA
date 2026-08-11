from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sentinel_dna.telemetry.adapters import TelemetryAdapter
from sentinel_dna.telemetry.models import SecurityAlert, TelemetryValidationError


class SentinelTelemetryAdapter(TelemetryAdapter):
    """
    Normalize Microsoft Sentinel / Log Analytics-style alert records into
    Sentinel DNA's vendor-neutral SecurityAlert model.

    This adapter intentionally performs no network calls and has no Azure SDK
    dependency. It is the normalization boundary for a future live Sentinel
    connector.
    """

    ENTITY_FIELDS = ("users", "hosts", "ips", "domains", "hashes")

    SEVERITY_MAP = {
        "informational": "informational",
        "information": "informational",
        "info": "informational",
        "low": "low",
        "medium": "medium",
        "moderate": "medium",
        "high": "high",
        "critical": "critical",
        "severe": "critical",
    }

    def normalize(self, raw_event: Any) -> SecurityAlert:
        event = self._validate_event(raw_event)

        alert_id = self._first_required_text(
            event,
            ("SystemAlertId", "AlertId", "id"),
            "alert ID",
        )

        title = self._first_required_text(
            event,
            ("AlertName", "title", "Title"),
            "title",
        )

        severity = self._normalize_severity(
            self._first_value(
                event,
                ("Severity", "severity"),
                default="medium",
            )
        )

        source = self._normalize_source(event)

        timestamp = self._optional_text(
            self._first_value(
                event,
                ("TimeGenerated", "timestamp", "Timestamp"),
                default="",
            )
        )

        description = self._optional_text(
            self._first_value(
                event,
                ("Description", "description"),
                default="",
            )
        )

        entities = self._normalize_entities(
            event.get("Entities", event.get("entities", {})),
            compromised_entity=event.get("CompromisedEntity"),
        )

        metadata = self._build_metadata(event)

        return SecurityAlert(
            alert_id=alert_id,
            source=source,
            timestamp=timestamp,
            title=title,
            severity=severity,
            description=description,
            entities=entities,
            raw_event=dict(event),
            metadata=metadata,
        )

    def _validate_event(self, raw_event: Any) -> dict[str, Any]:
        if not isinstance(raw_event, Mapping):
            raise TelemetryValidationError(
                "raw_event must be a dictionary or mapping"
            )

        return dict(raw_event)

    def _first_value(
        self,
        event: dict[str, Any],
        keys: tuple[str, ...],
        default: Any = None,
    ) -> Any:
        for key in keys:
            if key in event and event[key] is not None:
                return event[key]
        return default

    def _first_required_text(
        self,
        event: dict[str, Any],
        keys: tuple[str, ...],
        label: str,
    ) -> str:
        value = self._first_value(event, keys)

        if not isinstance(value, str) or not value.strip():
            raise TelemetryValidationError(f"missing required {label}")

        return value.strip()

    def _optional_text(self, value: Any, default: str = "") -> str:
        if value is None:
            return default

        if isinstance(value, str):
            return value.strip() or default

        return str(value).strip() or default

    def _normalize_severity(self, value: Any) -> str:
        normalized = self._optional_text(value, "medium").lower()

        return self.SEVERITY_MAP.get(normalized, "medium")

    def _normalize_source(self, event: dict[str, Any]) -> str:
        provider = self._optional_text(
            self._first_value(
                event,
                ("ProviderName", "provider", "Provider"),
                default="",
            )
        )

        product = self._optional_text(
            self._first_value(
                event,
                ("ProductName", "product", "Product"),
                default="",
            )
        )

        if provider and product:
            return f"{provider}/{product}"

        return provider or product or "microsoft-sentinel"

    def _normalize_entities(
        self,
        raw_entities: Any,
        compromised_entity: Any = None,
    ) -> dict[str, list[str]]:
        normalized = {field: [] for field in self.ENTITY_FIELDS}

        if raw_entities is None:
            raw_entities = {}

        if isinstance(raw_entities, Mapping):
            self._consume_entity_mapping(normalized, raw_entities)
        elif isinstance(raw_entities, list):
            for entity in raw_entities:
                self._consume_entity_item(normalized, entity)
        else:
            raise TelemetryValidationError(
                "Entities must be a dictionary or list"
            )

        if compromised_entity is not None:
            self._consume_compromised_entity(
                normalized,
                compromised_entity,
            )

        return {
            field: self._deduplicate(values)
            for field, values in normalized.items()
        }

    def _consume_entity_mapping(
        self,
        normalized: dict[str, list[str]],
        entities: Mapping[str, Any],
    ) -> None:
        aliases = {
            "users": "users",
            "user": "users",
            "accounts": "users",
            "account": "users",
            "hosts": "hosts",
            "host": "hosts",
            "computers": "hosts",
            "computer": "hosts",
            "ips": "ips",
            "ip": "ips",
            "domains": "domains",
            "domain": "domains",
            "hashes": "hashes",
            "hash": "hashes",
            "file_hashes": "hashes",
        }

        for key, values in entities.items():
            target = aliases.get(str(key).lower())
            if target is None:
                continue

            if isinstance(values, str):
                values = [values]

            if not isinstance(values, list):
                raise TelemetryValidationError(
                    f"Entities.{key} must be a list or string"
                )

            normalized[target].extend(
                self._clean_values(values)
            )

    def _consume_entity_item(
        self,
        normalized: dict[str, list[str]],
        entity: Any,
    ) -> None:
        if not isinstance(entity, Mapping):
            return

        entity_type = self._optional_text(
            entity.get("Type", entity.get("type", ""))
        ).lower()

        if entity_type in {"account", "user", "mailbox"}:
            value = self._extract_entity_value(
                entity,
                ("Name", "name", "UPNSuffix", "UserPrincipalName"),
            )
            if value:
                normalized["users"].append(value)

        elif entity_type in {
            "host",
            "hostname",
            "computer",
            "device",
        }:
            value = self._extract_entity_value(
                entity,
                ("HostName", "Hostname", "Name", "name"),
            )
            if value:
                normalized["hosts"].append(value)

        elif entity_type in {"ip", "ipaddress"}:
            value = self._extract_entity_value(
                entity,
                ("Address", "address", "IP", "ip"),
            )
            if value:
                normalized["ips"].append(value)

        elif entity_type in {"dns", "domain", "url"}:
            value = self._extract_entity_value(
                entity,
                ("DomainName", "domain", "Name", "name"),
            )
            if value:
                normalized["domains"].append(value)

        elif entity_type in {
            "filehash",
            "filehashentity",
            "hash",
        }:
            value = self._extract_entity_value(
                entity,
                ("Value", "value", "Hash", "hash"),
            )
            if value:
                normalized["hashes"].append(value)

    def _extract_entity_value(
        self,
        entity: Mapping[str, Any],
        keys: tuple[str, ...],
    ) -> str:
        for key in keys:
            value = entity.get(key)
            if value is not None:
                text = self._optional_text(value)
                if text:
                    return text

        return ""

    def _consume_compromised_entity(
        self,
        normalized: dict[str, list[str]],
        value: Any,
    ) -> None:
        if isinstance(value, list):
            normalized["hosts"].extend(self._clean_values(value))
            return

        text = self._optional_text(value)
        if text:
            normalized["hosts"].append(text)

    def _clean_values(self, values: list[Any]) -> list[str]:
        cleaned = []

        for value in values:
            text = self._optional_text(value)
            if text:
                cleaned.append(text)

        return cleaned

    def _deduplicate(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)

        return result

    def _build_metadata(self, event: dict[str, Any]) -> dict[str, Any]:
        metadata: dict[str, Any] = {}

        provider = self._optional_text(
            self._first_value(
                event,
                ("ProviderName", "provider", "Provider"),
                default="",
            )
        )

        product = self._optional_text(
            self._first_value(
                event,
                ("ProductName", "product", "Product"),
                default="",
            )
        )

        compromised_entity = event.get("CompromisedEntity")

        tactics = event.get("Tactics", event.get("tactics"))
        techniques = event.get("Techniques", event.get("techniques"))

        extended_properties = event.get(
            "ExtendedProperties",
            event.get("extended_properties"),
        )

        if provider:
            metadata["provider"] = provider

        if product:
            metadata["product"] = product

        if tactics is not None:
            metadata["tactics"] = self._normalize_metadata_value(tactics)

        if techniques is not None:
            metadata["techniques"] = self._normalize_metadata_value(
                techniques
            )

        if compromised_entity is not None:
            metadata["compromised_entity"] = compromised_entity

        if extended_properties is not None:
            if not isinstance(extended_properties, Mapping):
                raise TelemetryValidationError(
                    "ExtendedProperties must be a dictionary"
                )

            metadata["extended_properties"] = dict(
                extended_properties
            )

        return metadata

    def _normalize_metadata_value(self, value: Any) -> Any:
        if isinstance(value, str):
            parts = [
                part.strip()
                for part in value.split(",")
                if part.strip()
            ]
            return parts if len(parts) > 1 else value.strip()

        if isinstance(value, (list, tuple)):
            return [
                self._optional_text(item)
                for item in value
                if self._optional_text(item)
            ]

        return value