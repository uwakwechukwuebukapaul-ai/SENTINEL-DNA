"""
Sentinel DNA Analyst Workspace

Central analyst-facing intelligence layer.

Transforms investigation execution output into
SOC analyst workspace data.

Pipeline:

InvestigationResult
        |
        v
AnalystWorkspace
        |
        +--> Investigation View
        |
        +--> Evidence Formatter
        |
        +--> Timeline Builder
        |
        v
Analyst Dashboard Payload
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Optional

try:
    EvidenceFormatter = import_module(
        ".evidence_formatter",
        __package__,
    ).EvidenceFormatter
except (ImportError, AttributeError):
    class EvidenceFormatter:
        """Fallback used when evidence_formatter is unavailable."""

        def format(self, data: dict[str, Any]) -> Any:
            evidence = data.get("evidence", [])
            return evidence


try:
    InvestigationView = import_module(
        ".investigation_view",
        __package__,
    ).InvestigationView
except (ImportError, AttributeError):
    class InvestigationView:
        """Fallback used when investigation_view is unavailable."""

        def build(self, data: dict[str, Any]) -> dict[str, Any]:
            summary = data.get("summary", {})
            return summary if isinstance(summary, dict) else {}


try:
    TimelineBuilder = import_module(
        ".timeline_builder",
        __package__,
    ).TimelineBuilder
except (ImportError, AttributeError):
    class TimelineBuilder:
        """Fallback used when timeline_builder is not installed."""

        def build(self, data: dict[str, Any]) -> list[Any]:
            timeline = data.get("timeline", [])
            return timeline if isinstance(timeline, list) else []


class AnalystWorkspace:
    """
    Enterprise analyst workspace builder.

    Converts backend intelligence results into
    analyst-consumable views.
    """

    def __init__(
        self,
        investigation_view: Optional[InvestigationView] = None,
        evidence_formatter: Optional[EvidenceFormatter] = None,
        timeline_builder: Optional[TimelineBuilder] = None,
    ) -> None:

        self.investigation_view = (
            investigation_view
            if investigation_view is not None
            else InvestigationView()
        )

        self.evidence_formatter = (
            evidence_formatter
            if evidence_formatter is not None
            else EvidenceFormatter()
        )

        self.timeline_builder = (
            timeline_builder
            if timeline_builder is not None
            else TimelineBuilder()
        )


    def build(
        self,
        investigation: Any,
    ) -> dict[str, Any]:
        """
        Build analyst workspace.

        Supports:

        - InvestigationResult object
        - dictionary payload
        - serialized results
        """

        data = self._normalize(
            investigation
        )


        return {

            "case_id":
                data.get(
                    "case_id"
                ),

            "summary":
                self.investigation_view.build(
                    data
                ),

            "evidence":
                self.evidence_formatter.format(
                    data
                ),

            "timeline":
                self.timeline_builder.build(
                    data
                ),

            "metadata": {

                "workspace":
                    "Sentinel DNA Analyst Workspace",

                "status":
                    "ready",

            },
        }


    def from_result(
        self,
        result: Any,
    ) -> dict[str, Any]:
        """
        Compatibility alias.

        Used by investigation services.
        """

        return self.build(
            result
        )


    @staticmethod
    def _normalize(
        value: Any,
    ) -> dict[str, Any]:
        """
        Normalize incoming objects.
        """

        if value is None:
            return {}


        if isinstance(
            value,
            dict,
        ):
            return dict(value)


        if hasattr(
            value,
            "to_dict",
        ):

            try:
                return value.to_dict()

            except Exception:
                pass


        if hasattr(
            value,
            "__dict__",
        ):

            return {
                key: item
                for key, item
                in vars(value).items()
                if not key.startswith("_")
            }


        return {}