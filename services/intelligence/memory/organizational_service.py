"""Application service for tenant-safe organizational cyber memory."""
from __future__ import annotations

from typing import Any, Iterable

from .memory_service import MemoryService, _tokens
from .organizational_consolidator import ConsolidationResult, OrganizationalMemoryConsolidator
from .organizational_models import (
    AnalystKnowledgeEntry,
    AttackCampaignMemory,
    DetectionLearningRecord,
    InvestigationPattern,
    OrganizationalMemoryRecord,
    ResponsePlaybookMemory,
)
from .organizational_repository import OrganizationalMemoryRepository
from .similarity import DeterministicSimilarityProvider, MemorySimilarityProvider


class OrganizationalMemoryService:
    """Consolidate validated evidence and return advisory future context."""

    def __init__(
        self,
        repository: OrganizationalMemoryRepository | None = None,
        *,
        investigation_memory: MemoryService | None = None,
        similarity_provider: MemorySimilarityProvider | None = None,
    ) -> None:
        self.repository = repository or OrganizationalMemoryRepository()
        self.investigation_memory = investigation_memory
        self.similarity_provider = similarity_provider or DeterministicSimilarityProvider()
        self.consolidator = OrganizationalMemoryConsolidator(self.repository, self.similarity_provider)

    @staticmethod
    def _record_id(record: OrganizationalMemoryRecord) -> str:
        data = record.to_dict()
        for key in ("pattern_id", "campaign_id", "knowledge_id", "detection_id", "playbook_memory_id"):
            if data.get(key):
                return str(data[key])
        return "unknown"

    @staticmethod
    def _tokens(record: OrganizationalMemoryRecord) -> list[str]:
        data = record.to_dict()
        values: list[Any] = [data.get("description"), data.get("pattern_key"), data.get("campaign_key"), data.get("resolution_pattern"), data.get("detection_rule_id"), data.get("playbook_id"), data.get("analyst_verdict")]
        values.extend(data.get("attack_pattern", []) or [])
        values.extend(data.get("mitre_techniques", []) or [])
        values.extend(data.get("indicators", []) or [])
        values.extend(data.get("relationships", []) or [])
        return sorted(_tokens(values))

    def retrieve_advisory_context(
        self,
        tenant_id: str,
        *,
        case_id: str,
        alert: dict[str, Any],
        artifacts: list[dict[str, Any]],
        limit: int = 20,
    ) -> dict[str, Any]:
        tenant_id = str(tenant_id or "").strip()
        if not tenant_id:
            raise ValueError("organizational_memory_tenant_id_required")
        query_values: list[Any] = [alert.get("type"), alert.get("category"), alert.get("title")]
        for item in artifacts or []:
            if isinstance(item, dict):
                query_values.extend(item.get(key) for key in ("type", "category", "source", "technique", "tactic", "value", "indicator"))
        records = self.repository.list(tenant_id, limit=max(1, int(limit)))
        scored = self.similarity_provider.rank(
            query_values,
            [(self._record_id(record), self._tokens(record)) for record in records],
        )
        by_id = {self._record_id(record): record for record in records}
        scored = scored[: max(1, int(limit))]
        return {
            "status": "available" if scored else "no_history",
            "historical_organizational_memory": [by_id[item["record_id"]].to_dict() for item in scored],
            "similarity_scores": scored,
            "provider": self.similarity_provider.provider_name,
            "provenance": {
                "source": "organizational_cyber_memory",
                "tenant_id": tenant_id,
                "case_id": str(case_id),
                "memory_record_ids": [item["record_id"] for item in scored],
                "advisory_only": True,
                "deterministic": True,
            },
            "advisory_only": True,
            "deterministic": True,
        }

    def consolidate_completed_investigation(
        self,
        *,
        tenant_id: str,
        investigation_id: str,
        validated_findings: Iterable[Any] = (),
        mitre_mappings: Iterable[Any] = (),
        ioc_relationships: Iterable[Any] = (),
        created_by: str | None = None,
        observed_at: str | None = None,
    ) -> ConsolidationResult:
        if self.investigation_memory is None:
            raise RuntimeError("investigation_memory_source_required")
        records = self.investigation_memory.retrieve_historical_investigations(
            tenant_id, investigation_id=str(investigation_id), limit=10
        )
        if not records:
            raise LookupError("source_investigation_memory_not_found")
        feedback = self.investigation_memory.repository.list_feedback(tenant_id, str(investigation_id))
        return self.consolidator.consolidate_completed_investigation(
            tenant_id=tenant_id,
            investigation=records[0],
            analyst_feedback=feedback,
            validated_findings=validated_findings,
            mitre_mappings=mitre_mappings,
            ioc_relationships=ioc_relationships,
            created_by=created_by,
            observed_at=observed_at,
        )

    def consolidate_feedback(
        self,
        *,
        tenant_id: str,
        investigation_id: str,
        feedback: Any,
        created_by: str | None = None,
    ) -> ConsolidationResult:
        if self.investigation_memory is None:
            raise RuntimeError("investigation_memory_source_required")
        records = self.investigation_memory.retrieve_historical_investigations(
            tenant_id, investigation_id=str(investigation_id), limit=10
        )
        if not records:
            raise LookupError("source_investigation_memory_not_found")
        return self.consolidator.consolidate_completed_investigation(
            tenant_id=tenant_id,
            investigation=records[0],
            analyst_feedback=[feedback],
            created_by=created_by,
        )


__all__ = ["OrganizationalMemoryService"]
