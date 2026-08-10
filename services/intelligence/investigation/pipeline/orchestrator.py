"""
Sentinel DNA Investigation Pipeline Orchestrator.

Coordinates the complete investigation intelligence pipeline:

    Input
      |
      v
    Evidence Intelligence
      |
      v
    IOC Intelligence
      |
      v
    Threat Intelligence
      |
      v
    Graph Intelligence
      |
      v
    Timeline Intelligence
      |
      v
    Integration Intelligence
      |
      v
    Unified Investigation Result

The orchestrator is intentionally kept as a coordination layer.
Domain-specific intelligence remains implemented by the individual
intelligence engines.

Architecture rule:

    models.py
        ↓
    orchestrator.py

The orchestrator must never define the pipeline result model itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional

from ..evidence import EvidenceIntelligenceEngine
from ..ioc import IOCIntelligenceEngine
from ..threat import ThreatIntelligenceEngine
from ..graph import InvestigationGraphEngine
from ..timeline import InvestigationTimelineEngine
from ..integration import (
    InvestigationIntelligenceIntegrationEngine,
)

from .models import (
    InvestigationPipelineResult,
    InvestigationPipelineStage,
)


class InvestigationPipelineOrchestrator:
    """
    Enterprise investigation intelligence pipeline.

    The orchestrator coordinates intelligence engines but does not
    duplicate their domain logic.
    """

    def __init__(
        self,
        evidence_engine: Optional[
            EvidenceIntelligenceEngine
        ] = None,
        ioc_engine: Optional[
            IOCIntelligenceEngine
        ] = None,
        threat_engine: Optional[
            ThreatIntelligenceEngine
        ] = None,
        graph_engine: Optional[
            InvestigationGraphEngine
        ] = None,
        timeline_engine: Optional[
            InvestigationTimelineEngine
        ] = None,
        integration_engine: Optional[
            InvestigationIntelligenceIntegrationEngine
        ] = None,
    ) -> None:

        self.evidence_engine = (
            evidence_engine
            or EvidenceIntelligenceEngine()
        )

        self.ioc_engine = (
            ioc_engine
            or IOCIntelligenceEngine()
        )

        self.threat_engine = (
            threat_engine
            or ThreatIntelligenceEngine()
        )

        self.graph_engine = (
            graph_engine
            or InvestigationGraphEngine()
        )

        self.timeline_engine = (
            timeline_engine
            or InvestigationTimelineEngine()
        )

        self.integration_engine = (
            integration_engine
            or InvestigationIntelligenceIntegrationEngine()
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def investigate(
        self,
        case_id: str,
        investigation: Any,
    ) -> InvestigationPipelineResult:
        """
        Execute the complete investigation intelligence pipeline.
        """

        normalized_input = self._normalize_input(
            investigation
        )

        stages: list[str] = []

        # --------------------------------------------------------------
        # 1. Evidence Intelligence
        # --------------------------------------------------------------

        evidence_collection = (
            self._build_evidence_collection(
                normalized_input
            )
        )

        evidence_context = (
            self.evidence_engine.build_evidence_context(
                evidence_collection
            )
        )

        evidence_items = (
            self._extract_collection_items(
                evidence_collection
            )
        )

        stages.append(
            InvestigationPipelineStage.EVIDENCE.value
        )

        # --------------------------------------------------------------
        # 2. IOC Intelligence
        # --------------------------------------------------------------

        indicators = (
            self._extract_indicators(
                evidence_items,
                evidence_context,
            )
        )

        ioc_result = (
            self.ioc_engine.enrich(
                case_id,
                indicators,
            )
        )

        iocs = self._result_items(
            ioc_result,
            (
                "iocs",
                "indicators",
                "results",
            ),
        )

        stages.append(
            InvestigationPipelineStage.IOC.value
        )

        # --------------------------------------------------------------
        # 3. Threat Intelligence
        # --------------------------------------------------------------

        threat_result = (
            self.threat_engine.correlate(
                case_id,
                iocs,
            )
        )

        threats = self._result_items(
            threat_result,
            (
                "threats",
                "results",
            ),
        )

        stages.append(
            InvestigationPipelineStage.THREAT.value
        )

        # --------------------------------------------------------------
        # 4. Investigation Graph
        # --------------------------------------------------------------

        graph_result = (
            self.graph_engine.build(
                case_id,
                evidence_items,
                iocs,
                threats,
            )
        )

        stages.append(
            InvestigationPipelineStage.GRAPH.value
        )

        # --------------------------------------------------------------
        # 5. Investigation Timeline
        # --------------------------------------------------------------

        timeline_result = (
            self.timeline_engine.build(
                case_id,
                evidence=evidence_items,
                iocs=iocs,
                threats=threats,
            )
        )

        stages.append(
            InvestigationPipelineStage.TIMELINE.value
        )

        # --------------------------------------------------------------
        # 6. Intelligence Integration
        # --------------------------------------------------------------

        integration_result = (
            self.integration_engine.integrate(
                case_id,
                evidence=evidence_items,
                iocs=iocs,
                threats=threats,
                graph=graph_result,
                timeline=timeline_result,
            )
        )

        stages.append(
            InvestigationPipelineStage.INTEGRATION.value
        )

        # --------------------------------------------------------------
        # Final risk / confidence
        # --------------------------------------------------------------

        risk = self._resolve_risk(
            integration_result,
            threats,
            iocs,
            evidence_items,
        )

        confidence = self._resolve_confidence(
            integration_result,
            threats,
            iocs,
        )

        metadata = {
            "engine":
                "investigation_pipeline_orchestrator",

            "stage_count":
                len(stages),

            "stages":
                stages,

            "evidence_count":
                len(evidence_items),

            "ioc_count":
                len(iocs),

            "threat_count":
                len(threats),

            "risk":
                risk,

            "confidence":
                confidence,
        }

        return InvestigationPipelineResult(
            case_id=case_id,
            status="completed",
            evidence=evidence_context,
            iocs=iocs,
            threats=threats,
            graph=graph_result,
            timeline=timeline_result,
            integration=integration_result,
            risk=risk,
            confidence=confidence,
            stages=stages,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Backward-compatible API
    # ------------------------------------------------------------------

    def run(
        self,
        case_id: str,
        investigation: Any,
    ) -> InvestigationPipelineResult:
        """
        Backward-compatible alias for investigate().
        """

        return self.investigate(
            case_id,
            investigation,
        )

    # ------------------------------------------------------------------
    # Input normalization
    # ------------------------------------------------------------------

    def _normalize_input(
        self,
        investigation: Any,
    ) -> Any:

        if investigation is None:
            return []

        if isinstance(
            investigation,
            Mapping,
        ):
            return [
                dict(investigation)
            ]

        if isinstance(
            investigation,
            (list, tuple, set),
        ):
            return list(
                investigation
            )

        return [
            investigation
        ]

    def _build_evidence_collection(
        self,
        investigation: Any,
    ) -> Any:

        if hasattr(
            investigation,
            "artifacts",
        ):
            return investigation

        artifacts = self._normalize_artifacts(
            investigation
        )

        collection_type = (
            self._resolve_evidence_collection_type()
        )

        if collection_type is None:
            return self._FallbackEvidenceCollection(
                artifacts=artifacts
            )

        constructors = (
            lambda: collection_type(
                artifacts=artifacts
            ),
            lambda: collection_type(
                items=artifacts
            ),
            lambda: collection_type(
                artifacts
            ),
        )

        for constructor in constructors:
            try:
                collection = constructor()

                if hasattr(
                    collection,
                    "artifacts",
                ):
                    return collection

                if hasattr(
                    collection,
                    "items",
                ):
                    return self._FallbackEvidenceCollection(
                        artifacts=list(
                            collection.items
                        )
                    )

            except (
                TypeError,
                ValueError,
            ):
                continue

        return self._FallbackEvidenceCollection(
            artifacts=artifacts
        )

    def _normalize_artifacts(
        self,
        investigation: Any,
    ) -> list[Any]:

        if investigation is None:
            return []

        if hasattr(
            investigation,
            "artifacts",
        ):
            return list(
                getattr(
                    investigation,
                    "artifacts",
                )
                or []
            )

        if isinstance(
            investigation,
            Mapping,
        ):
            return [
                dict(investigation)
            ]

        if isinstance(
            investigation,
            (list, tuple, set),
        ):
            return list(
                investigation
            )

        return [
            investigation
        ]

    def _resolve_evidence_collection_type(
        self,
    ):

        candidates = (
            "services.intelligence.investigation.evidence.models",
            "services.intelligence.models",
        )

        import importlib

        for module_name in candidates:

            try:
                module = importlib.import_module(
                    module_name
                )

            except ImportError:
                continue

            collection_type = getattr(
                module,
                "EvidenceCollection",
                None,
            )

            if collection_type is not None:
                return collection_type

        return None

    def _extract_collection_items(
        self,
        collection: Any,
    ) -> list[Any]:

        if collection is None:
            return []

        artifacts = getattr(
            collection,
            "artifacts",
            None,
        )

        if artifacts is not None:
            return list(
                artifacts
            )

        items = getattr(
            collection,
            "items",
            None,
        )

        if items is not None:

            if callable(items):
                try:
                    return list(
                        items()
                    )
                except TypeError:
                    pass

            try:
                return list(
                    items
                )
            except TypeError:
                pass

        if isinstance(
            collection,
            (list, tuple, set),
        ):
            return list(
                collection
            )

        return [
            collection
        ]

    # ------------------------------------------------------------------
    # Indicator extraction
    # ------------------------------------------------------------------

    def _extract_indicators(
        self,
        evidence_items: Iterable[Any],
        evidence_context: Any = None,
    ) -> list[Any]:

        indicators: list[Any] = []

        if isinstance(
            evidence_context,
            Mapping,
        ):

            context_indicators = (
                evidence_context.get(
                    "indicators"
                )
                or evidence_context.get(
                    "iocs"
                )
                or []
            )

            if isinstance(
                context_indicators,
                (list, tuple, set),
            ):
                indicators.extend(
                    context_indicators
                )

        for artifact in evidence_items:

            if isinstance(
                artifact,
                Mapping,
            ):

                explicit = (
                    artifact.get(
                        "indicator"
                    )
                    or artifact.get(
                        "ioc"
                    )
                )

                if explicit:
                    indicators.append(
                        self._indicator_payload(
                            artifact,
                            explicit,
                        )
                    )
                    continue

                indicators_value = (
                    artifact.get(
                        "indicators"
                    )
                    or artifact.get(
                        "iocs"
                    )
                )

                if isinstance(
                    indicators_value,
                    (list, tuple, set),
                ):

                    for indicator in indicators_value:

                        if isinstance(
                            indicator,
                            Mapping,
                        ):
                            indicators.append(
                                dict(
                                    indicator
                                )
                            )
                        else:
                            indicators.append(
                                {
                                    "indicator":
                                        indicator
                                }
                            )

                    continue

                value = (
                    artifact.get(
                        "value"
                    )
                    or artifact.get(
                        "domain"
                    )
                    or artifact.get(
                        "url"
                    )
                    or artifact.get(
                        "ip"
                    )
                    or artifact.get(
                        "hash"
                    )
                )

                if value:
                    indicators.append(
                        self._indicator_payload(
                            artifact,
                            value,
                        )
                    )

                continue

            if isinstance(
                artifact,
                str,
            ):
                indicators.append(
                    {
                        "indicator":
                            artifact
                    }
                )

        return self._deduplicate_indicators(
            indicators
        )

    def _indicator_payload(
        self,
        artifact: Mapping[str, Any],
        value: Any,
    ) -> dict[str, Any]:

        payload = dict(
            artifact
        )

        payload[
            "indicator"
        ] = value

        return payload

    def _deduplicate_indicators(
        self,
        indicators: list[Any],
    ) -> list[Any]:

        result: list[Any] = []
        seen: set[str] = set()

        for indicator in indicators:

            if isinstance(
                indicator,
                Mapping,
            ):

                value = (
                    indicator.get(
                        "indicator"
                    )
                    or indicator.get(
                        "value"
                    )
                )

                key = str(
                    value
                ).strip().lower()

            else:
                key = str(
                    indicator
                ).strip().lower()

            if not key:
                continue

            if key in seen:
                continue

            seen.add(
                key
            )

            result.append(
                indicator
            )

        return result

    # ------------------------------------------------------------------
    # Result extraction
    # ------------------------------------------------------------------

    def _result_items(
        self,
        result: Any,
        keys: tuple[str, ...],
    ) -> list[Any]:

        if result is None:
            return []

        if isinstance(
            result,
            Mapping,
        ):

            for key in keys:

                value = result.get(
                    key
                )

                if value is not None:
                    return self._as_list(
                        value
                    )

        for key in keys:

            value = getattr(
                result,
                key,
                None,
            )

            if value is not None:
                return self._as_list(
                    value
                )

        if isinstance(
            result,
            (list, tuple, set),
        ):
            return list(
                result
            )

        return []

    def _as_list(
        self,
        value: Any,
    ) -> list[Any]:

        if value is None:
            return []

        if isinstance(
            value,
            list,
        ):
            return value

        if isinstance(
            value,
            (tuple, set),
        ):
            return list(
                value
            )

        return [
            value
        ]

    # ------------------------------------------------------------------
    # Risk / confidence
    # ------------------------------------------------------------------

    def _resolve_risk(
        self,
        integration_result: Any,
        threats: list[Any],
        iocs: list[Any],
        evidence_items: list[Any],
    ) -> str:

        integration_risk = self._read_value(
            integration_result,
            "risk",
        )

        if self._valid_risk(
            integration_risk
        ):
            return str(
                integration_risk
            ).lower()

        severity_values: list[str] = []

        for item in (
            list(threats)
            + list(iocs)
            + list(evidence_items)
        ):

            if not isinstance(
                item,
                Mapping,
            ):
                continue

            value = (
                item.get(
                    "severity"
                )
                or item.get(
                    "risk"
                )
            )

            if value:
                severity_values.append(
                    str(
                        value
                    ).lower()
                )

        return self._highest_risk(
            severity_values
        )

    def _resolve_confidence(
        self,
        integration_result: Any,
        threats: list[Any],
        iocs: list[Any],
    ) -> float:

        integration_confidence = (
            self._read_value(
                integration_result,
                "confidence",
            )
        )

        if integration_confidence is not None:

            try:
                return float(
                    integration_confidence
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

        values: list[float] = []

        for item in (
            list(threats)
            + list(iocs)
        ):

            if not isinstance(
                item,
                Mapping,
            ):
                continue

            confidence = item.get(
                "confidence"
            )

            if confidence is None:
                continue

            try:
                values.append(
                    float(
                        confidence
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

        if not values:
            return 0.0

        return round(
            sum(values)
            / len(values),
            2,
        )

    def _read_value(
        self,
        result: Any,
        key: str,
    ) -> Any:

        if result is None:
            return None

        if isinstance(
            result,
            Mapping,
        ):
            return result.get(
                key
            )

        return getattr(
            result,
            key,
            None,
        )

    def _valid_risk(
        self,
        risk: Any,
    ) -> bool:

        if risk is None:
            return False

        return str(
            risk
        ).lower() in {
            "critical",
            "high",
            "medium",
            "low",
            "informational",
            "info",
            "unknown",
        }

    def _highest_risk(
        self,
        values: Iterable[str],
    ) -> str:

        priority = {
            "unknown": 0,
            "informational": 1,
            "info": 1,
            "low": 2,
            "medium": 3,
            "high": 4,
            "critical": 5,
        }

        highest = "unknown"
        highest_score = 0

        for value in values:

            normalized = str(
                value
            ).lower()

            score = priority.get(
                normalized,
                0,
            )

            if score > highest_score:
                highest_score = score
                highest = normalized

        return highest

    # ------------------------------------------------------------------
    # Fallback evidence collection
    # ------------------------------------------------------------------

    @dataclass
    class _FallbackEvidenceCollection:

        artifacts: list[Any] = field(
            default_factory=list
        )


class InvestigationPipeline(
    InvestigationPipelineOrchestrator
):
    """
    Public compatibility facade.

    Existing callers can continue using:

        InvestigationPipeline().run(...)

    while the architecture internally uses the enterprise
    InvestigationPipelineOrchestrator.
    """

    pass