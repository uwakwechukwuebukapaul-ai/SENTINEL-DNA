"""Deterministic, evidence-only attack sequence reconstruction."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from .models import AttackSequenceEvent, AttackSequenceResult


class AttackSequenceAnalyzer:
    """Reconstruct source-backed stages without creating investigative facts."""

    # Provider-neutral rules: a technique is emitted only when the source text
    # itself contains the observable named by the rule.
    _TECHNIQUE_RULES = (
        ("powershell", "T1059.001", "execution"),
    )
    _REFERENCE_KEYS = ("evidence_references", "evidence_refs", "evidence_ids", "evidence_id")
    _IOC_REFERENCE_KEYS = ("ioc_references", "ioc_refs", "ioc_ids", "ioc_id")
    _MITRE_KEYS = ("mitre_techniques", "mitre", "attack_techniques")

    def analyze(
        self,
        result: Any,
        *,
        tenant_id: str | None = None,
        timeline: Any = None,
        evidence: Any = None,
        iocs: Any = None,
        fusion: Any = None,
    ) -> AttackSequenceResult:
        data = self._data(result)
        owner = self._tenant(data)
        if tenant_id and owner and str(tenant_id) != owner:
            raise PermissionError("attack sequence tenant does not match investigation tenant")
        scoped_tenant = str(tenant_id or owner) if tenant_id or owner else None
        investigation_id = str(data.get("investigation_id") or data.get("case_id") or "") or None

        evidence_index = self._references(evidence if evidence is not None else self._items(data.get("evidence")) + self._items(data.get("artifacts")), scoped_tenant)
        ioc_index = self._references(iocs if iocs is not None else data.get("iocs"), scoped_tenant)
        supported_techniques = self._supported_techniques(data, fusion, scoped_tenant)
        source_timeline = self._items(timeline if timeline is not None else data.get("timeline"))
        events: list[AttackSequenceEvent] = []
        missing: list[dict[str, Any]] = []

        for item in source_timeline:
            event, gaps = self._event(item, evidence_index, ioc_index, supported_techniques, scoped_tenant)
            missing.extend(gaps)
            if event is not None:
                events.append(event)

        events.sort(key=lambda event: (self._sort_timestamp(event.timestamp), event.timestamp, event.event_id))
        uncertainty: list[str] = []
        if not source_timeline:
            uncertainty.append("No source-backed timeline events were supplied.")
        if not events and source_timeline:
            uncertainty.append("Timeline events lacked required stable identifiers, timestamps, or evidence references.")
        if not ioc_index:
            uncertainty.append("No tenant-authorized IOC references were available.")
        if not supported_techniques:
            uncertainty.append("No evidence-supported MITRE ATT&CK techniques were available.")

        mitre_summary = self._mitre_summary(events)
        confidence = round(sum(event.confidence for event in events) / len(events), 2) if events else 0.0
        event_ids = ", ".join(event.event_id for event in events)
        story = (
            f"Evidence-backed attack sequence reconstructed from event(s): {event_ids}."
            if events else "No evidence-backed attack sequence could be reconstructed."
        )
        return AttackSequenceResult(
            investigation_id=investigation_id,
            tenant_id=scoped_tenant,
            events=events,
            attack_story=story,
            mitre_summary=mitre_summary,
            confidence=confidence,
            uncertainty=uncertainty,
            missing_evidence=self._unique(missing),
            provenance={
                "analyzer": "attack_sequence_analyzer",
                "timeline_event_count": len(source_timeline),
                "accepted_event_count": len(events),
                "evidence_reference_count": len(evidence_index),
                "ioc_reference_count": len(ioc_index),
                "tenant_id": scoped_tenant,
            },
        )

    @staticmethod
    def _data(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        return {}

    @staticmethod
    def _items(value: Any) -> list[Any]:
        return list(value) if isinstance(value, (list, tuple, set)) else ([] if value is None else [value])

    @staticmethod
    def _tenant(data: dict[str, Any]) -> str | None:
        context = data.get("tenant_context") if isinstance(data.get("tenant_context"), dict) else {}
        return str(data.get("tenant_id") or context.get("tenant_id") or "") or None

    def _references(self, values: Any, tenant_id: str | None) -> dict[str, dict[str, Any]]:
        references: dict[str, dict[str, Any]] = {}
        for item in self._items(values):
            if not isinstance(item, dict):
                continue
            if tenant_id and item.get("tenant_id") not in (None, tenant_id):
                continue
            reference = next((item.get(key) for key in ("evidence_id", "artifact_id", "ioc_id", "id", "reference_id", "reference") if item.get(key)), None)
            if reference:
                references.setdefault(str(reference), dict(item))
        return references

    def _event(self, item: Any, evidence: dict[str, dict[str, Any]], iocs: dict[str, dict[str, Any]], supported: set[str], tenant_id: str | None) -> tuple[AttackSequenceEvent | None, list[dict[str, Any]]]:
        if not isinstance(item, dict):
            return None, [{"reason": "timeline_event_not_structured"}]
        if tenant_id and item.get("tenant_id") not in (None, tenant_id):
            return None, []
        event_id = item.get("event_id") or item.get("id")
        timestamp = item.get("timestamp") or item.get("event_time") or item.get("occurred_at")
        missing: list[dict[str, Any]] = []
        if not event_id:
            missing.append({"reason": "timeline_event_id_missing"})
        if not timestamp:
            missing.append({"event_id": str(event_id) if event_id else None, "reason": "timeline_timestamp_missing"})
        evidence_refs = self._event_references(item, self._REFERENCE_KEYS, evidence)
        requested_evidence = self._requested(item, self._REFERENCE_KEYS)
        if not evidence_refs:
            missing.append({"event_id": str(event_id) if event_id else None, "reason": "evidence_reference_missing_or_unavailable"})
        if requested_evidence - set(evidence_refs):
            missing.append({"event_id": str(event_id) if event_id else None, "reason": "referenced_evidence_unavailable", "references": sorted(requested_evidence - set(evidence_refs))})
        if missing:
            return None, missing
        ioc_refs = self._event_references(item, self._IOC_REFERENCE_KEYS, iocs)
        requested_iocs = self._requested(item, self._IOC_REFERENCE_KEYS)
        if requested_iocs - set(ioc_refs):
            missing.append({"event_id": str(event_id), "reason": "referenced_ioc_unavailable", "references": sorted(requested_iocs - set(ioc_refs))})
        techniques, stage = self._techniques(item, evidence_refs, supported)
        description = str(item.get("description") or item.get("event") or item.get("value") or item.get("event_type") or "")
        if not description:
            description = str(item.get("event_type") or "source event")
        explicit_confidence = item.get("confidence")
        confidence = self._confidence(explicit_confidence, evidence_refs, ioc_refs, techniques)
        provenance = {"source": item.get("source", "timeline"), "event_type": item.get("event_type") or item.get("type"), "evidence_sources": sorted({str(evidence[ref].get("source", "unknown")) for ref in evidence_refs})}
        return AttackSequenceEvent(str(event_id), str(timestamp), stage, description, evidence_refs, ioc_refs, techniques, confidence, provenance), missing

    def _requested(self, item: dict[str, Any], keys: Iterable[str]) -> set[str]:
        values: set[str] = set()
        for key in keys:
            value = item.get(key)
            for entry in self._items(value):
                if entry:
                    values.add(str(entry))
        return values

    def _event_references(self, item: dict[str, Any], keys: Iterable[str], known: dict[str, dict[str, Any]]) -> list[str]:
        return sorted(reference for reference in self._requested(item, keys) if reference in known)

    def _supported_techniques(self, data: dict[str, Any], fusion: Any, tenant_id: str | None) -> set[str]:
        techniques = {str(value) for value in self._items(data.get("mitre")) if isinstance(value, str) and value}
        for source in self._items(fusion):
            if not isinstance(source, dict) or (tenant_id and source.get("tenant_id") not in (None, tenant_id)):
                continue
            for key in self._MITRE_KEYS:
                techniques.update(str(value) for value in self._items(source.get(key)) if value)
        intelligence = data.get("intelligence") if isinstance(data.get("intelligence"), dict) else {}
        metadata = intelligence.get("normalized", {}).get("metadata", {}) if isinstance(intelligence.get("normalized"), dict) else {}
        for source in self._items(metadata.get("intelligence_status", {}).get("fusion_results", []) if isinstance(metadata.get("intelligence_status"), dict) else []):
            if isinstance(source, dict):
                techniques.update(str(value) for value in self._items(source.get("attack_techniques")) if value)
        return techniques

    def _techniques(self, item: dict[str, Any], evidence_refs: list[str], supported: set[str]) -> tuple[list[str], str]:
        explicit = {str(value) for key in self._MITRE_KEYS for value in self._items(item.get(key)) if value}
        techniques = sorted(explicit & supported)
        text = " ".join(str(item.get(key, "")) for key in ("description", "event", "value", "event_type", "type")).lower()
        stage = str(item.get("stage") or item.get("attack_phase") or item.get("phase") or "unclassified")
        for observable, technique, mapped_stage in self._TECHNIQUE_RULES:
            if observable in text and evidence_refs and technique in supported:
                if technique not in techniques:
                    techniques.append(technique)
                if stage == "unclassified":
                    stage = mapped_stage
        return sorted(techniques), stage

    @staticmethod
    def _confidence(value: Any, evidence_refs: list[str], ioc_refs: list[str], techniques: list[str]) -> float:
        if value is not None:
            try:
                score = float(value)
                return max(0.0, min(100.0, score * 100 if 0 <= score <= 1 else score))
            except (TypeError, ValueError):
                pass
        return min(100.0, 50.0 + min(30.0, len(evidence_refs) * 30.0) + (10.0 if ioc_refs else 0.0) + (10.0 if techniques else 0.0))

    @staticmethod
    def _sort_timestamp(timestamp: str) -> tuple[int, datetime | str]:
        text = str(timestamp)
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return 0, parsed.astimezone(timezone.utc)
        except ValueError:
            return 1, text

    @staticmethod
    def _mitre_summary(events: list[AttackSequenceEvent]) -> list[dict[str, Any]]:
        references: dict[str, set[str]] = {}
        for event in events:
            for technique in event.mitre_techniques:
                references.setdefault(technique, set()).update(event.evidence_references)
        return [{"technique_id": technique, "evidence_references": sorted(refs)} for technique, refs in sorted(references.items())]

    @staticmethod
    def _unique(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        seen: set[tuple[tuple[str, str], ...]] = set()
        for value in values:
            key = tuple(sorted((str(name), str(content)) for name, content in value.items()))
            if key not in seen:
                seen.add(key)
                output.append(value)
        return output
