"""
Sentinel DNA Investigation Runtime API.

Provides the stable service-facing entrypoint for autonomous
investigation execution.

This module intentionally keeps transport concerns separate from
investigation intelligence. Flask/API adapters can call this layer
without coupling themselves to the internal investigation stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .investigator import AIInvestigator
from .models import InvestigationRuntimeResult


@dataclass(slots=True)
class InvestigationRuntimeRequest:
    """
    Input contract for an investigation runtime execution.
    """

    case_id: str
    evidence: Any

    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("case_id is required")

        if self.metadata is None:
            self.metadata = {}


class InvestigationRuntimeAPI:
    """
    Stable application-facing facade for the AI Investigator runtime.

    The facade protects callers from internal pipeline changes while
    preserving a deterministic execution contract.
    """

    def __init__(
        self,
        investigator: AIInvestigator | None = None,
    ) -> None:
        self.investigator = (
            investigator
            if investigator is not None
            else AIInvestigator()
        )

    def investigate(
        self,
        case_id: str,
        evidence: Any,
        metadata: dict[str, Any] | None = None,
    ) -> InvestigationRuntimeResult:
        """
        Execute an autonomous investigation.

        Parameters
        ----------
        case_id:
            Unique investigation/case identifier.

        evidence:
            Evidence supplied to the investigator runtime.

        metadata:
            Optional request-level metadata.

        Returns
        -------
        InvestigationRuntimeResult
            Structured investigation result.
        """

        request = InvestigationRuntimeRequest(
            case_id=case_id,
            evidence=evidence,
            metadata=metadata,
        )

        result = self.investigator.investigate(
            case_id=request.case_id,
            evidence=request.evidence,
        )

        self._attach_request_metadata(
            result,
            request.metadata or {},
        )

        return result

    def execute(
        self,
        request: InvestigationRuntimeRequest,
    ) -> InvestigationRuntimeResult:
        """
        Execute a pre-built runtime request.

        This method is useful for workers, queues, schedulers,
        and future SOAR integrations.
        """

        result = self.investigator.investigate(
            case_id=request.case_id,
            evidence=request.evidence,
        )

        self._attach_request_metadata(
            result,
            request.metadata or {},
        )

        return result

    @staticmethod
    def _attach_request_metadata(
        result: InvestigationRuntimeResult,
        metadata: dict[str, Any],
    ) -> None:
        """
        Attach request metadata without replacing runtime metadata.
        """

        if not metadata:
            return

        existing = getattr(
            result,
            "execution_metadata",
            None,
        )

        if existing is None:
            existing = {}

            try:
                result.execution_metadata = existing
            except AttributeError:
                return

        existing["request_metadata"] = dict(metadata)


_default_runtime_api: InvestigationRuntimeAPI | None = None


def get_investigation_runtime() -> InvestigationRuntimeAPI:
    """
    Return the process-local default investigation runtime.

    Keeping construction lazy prevents application startup from
    instantiating investigation components unnecessarily.
    """

    global _default_runtime_api

    if _default_runtime_api is None:
        _default_runtime_api = InvestigationRuntimeAPI()

    return _default_runtime_api


def investigate(
    case_id: str,
    evidence: Any,
    metadata: dict[str, Any] | None = None,
) -> InvestigationRuntimeResult:
    """
    Convenience function for application integrations.
    """

    return get_investigation_runtime().investigate(
        case_id=case_id,
        evidence=evidence,
        metadata=metadata,
    )


__all__ = [
    "InvestigationRuntimeAPI",
    "InvestigationRuntimeRequest",
    "get_investigation_runtime",
    "investigate",
]