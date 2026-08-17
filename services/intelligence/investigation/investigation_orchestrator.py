"""
Sentinel DNA Investigation Orchestrator

Enterprise investigation execution coordinator.

Responsibilities
----------------
- Normalize investigation input.
- Maintain execution history.
- Coordinate correlation, fusion, and reasoning.
- Normalize heterogeneous intelligence outputs.
- Produce a stable InvestigationResult contract.
- Preserve compatibility with legacy intelligence engines.
- Keep empty investigations deterministic and successful.
- Preserve execution metadata for downstream reporting.

Architecture

    Artifacts
        |
        v
    InvestigationOrchestrator
        |
        +--> CorrelationEngine
        |
        +--> FusionEngine
        |
        +--> ReasoningEngine
        |
        v
    InvestigationResult
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from services.intelligence.correlation import CorrelationEngine
from services.intelligence.fusion import (
    FusionEngine,
    IntelligenceDecisionGovernance,
    ProviderNeutralFusionEngine,
)
from app.intelligence.gateway import IOC, IntelligenceObservation

from .investigation_result import InvestigationResult


class InvestigationOrchestrator:
    """
    Central coordinator for Sentinel DNA investigation execution.

    The orchestrator owns workflow coordination only. Intelligence
    logic remains inside the individual intelligence services.
    """

    def __init__(
        self,
        correlation_engine: Optional[CorrelationEngine] = None,
        fusion_engine: Optional[FusionEngine] = None,
        reasoning_engine: Any = None,
    ) -> None:
        self.correlation_engine = (
            correlation_engine
            if correlation_engine is not None
            else CorrelationEngine()
        )

        self.fusion_engine = (
            fusion_engine
            if fusion_engine is not None
            else FusionEngine()
        )

        self.reasoning_engine = reasoning_engine

        self.execution_history: list[InvestigationResult] = []

        self.running = False

        self.last_result: Optional[InvestigationResult] = None

    # =========================================================
    # LIFECYCLE
    # =========================================================

    def start(self) -> bool:
        """
        Start the investigation orchestrator.
        """

        self.running = True

        return True

    def stop(self) -> bool:
        """
        Stop the investigation orchestrator.
        """

        self.running = False

        return True

    def clear_execution_history(self) -> bool:
        """
        Clear all previous investigation executions.
        """

        self.execution_history.clear()

        self.last_result = None

        return True

    # =========================================================
    # PUBLIC EXECUTION
    # =========================================================

    def investigate(
        self,
        artifacts: Optional[list[dict[str, Any]]] = None,
        case_id: Optional[str] = None,
        investigation_id: Optional[str] = None,
        context: Any = None,
        ioc: IOC | None = None,
        intelligence_observations: Optional[list[IntelligenceObservation]] = None,
    ) -> InvestigationResult:
        """
        Execute a complete investigation.

        Empty artifact lists are valid investigations and therefore
        produce a completed low-confidence result rather than an
        execution failure.
        """

        if not self.running:
            self.start()

        normalized_artifacts = self._normalize_artifacts(
            artifacts
        )

        started_at = self._timestamp()

        if investigation_id is None:
            investigation_id = (
                self._generate_investigation_id(
                    case_id
                )
            )

        try:
            correlation_signals = (
                self._build_correlation_signals(
                    normalized_artifacts
                )
            )

            correlation = self._correlate(
                signals=correlation_signals,
                case_id=case_id,
                context=context,
            )

            fusion = self._fuse(
                artifacts=normalized_artifacts,
                correlation=correlation,
                case_id=case_id,
                ioc=ioc,
                intelligence_observations=intelligence_observations,
            )

            reasoning = self._reason(
                artifacts=normalized_artifacts,
                correlation=correlation,
                fusion=fusion,
                context=context,
            )

            result = self._build_success_result(
                artifacts=normalized_artifacts,
                correlation=correlation,
                fusion=fusion,
                reasoning=reasoning,
                case_id=case_id,
                investigation_id=investigation_id,
                started_at=started_at,
                context=context,
            )

        except Exception as exc:
            result = self._build_failure_result(
                error=str(exc),
                case_id=case_id,
                investigation_id=investigation_id,
                started_at=started_at,
                artifacts=normalized_artifacts,
            )

        self.last_result = result

        self.execution_history.append(
            result
        )

        return result

    # Compatibility aliases.
    execute = investigate
    run = investigate

    # =========================================================
    # HISTORY
    # =========================================================

    def get_execution_history(
        self,
    ) -> list[InvestigationResult]:
        """
        Return a snapshot of investigation history.
        """

        return list(
            self.execution_history
        )

    def history(
        self,
    ) -> list[InvestigationResult]:
        """
        Compatibility alias for get_execution_history().
        """

        return self.get_execution_history()

    # =========================================================
    # CORRELATION
    # =========================================================

    def _correlate(
        self,
        signals: list[dict[str, Any]],
        case_id: Optional[str],
        context: Any = None,
    ) -> Any:
        """
        Execute correlation while supporting multiple engine
        signatures.

        Supported forms include:

            correlate(signals)

            correlate(
                signals=signals,
                case_id=case_id,
            )

            correlate(
                signals=signals,
                case_id=case_id,
                context=context,
            )
        """

        correlate: Callable[..., Any] = (
            self.correlation_engine.correlate
        )

        # Canonical current contract.
        try:
            return correlate(
                signals
            )
        except TypeError:
            pass

        # Extended contract.
        try:
            return correlate(
                signals=signals,
                case_id=case_id,
                context=context,
            )
        except TypeError:
            pass

        # Case-aware legacy contract.
        try:
            return correlate(
                signals=signals,
                case_id=case_id,
            )
        except TypeError:
            pass

        # Keyword-only signal contract.
        return correlate(
            signals=signals
        )

    # =========================================================
    # FUSION
    # =========================================================

    def _fuse(
        self,
        artifacts: list[dict[str, Any]],
        correlation: Any,
        case_id: Optional[str],
        ioc: IOC | None = None,
        intelligence_observations: Optional[list[IntelligenceObservation]] = None,
        context: Any = None,
    ) -> Any:
        """
        Execute threat fusion.

        Supports both:

            fuse(payload)

        and older two-payload implementations.
        """

        if ioc is not None and intelligence_observations is not None:
            return ProviderNeutralFusionEngine().fuse(
                ioc,
                intelligence_observations,
                context=context,
            )

        correlation_data = self._as_dict(
            correlation
        )

        payload = {
            "case_id": case_id,
            "artifacts": list(
                artifacts
            ),
            "correlation": correlation_data,
            "risk_score": self._extract_risk_score(
                correlation
            ),
            "indicators": list(
                artifacts
            ),
        }

        fuse = self.fusion_engine.fuse

        try:
            return fuse(
                payload
            )
        except TypeError:
            return fuse(
                {
                    "case_id": case_id,
                },
                payload,
            )

    # =========================================================
    # REASONING
    # =========================================================

    def _reason(
        self,
        artifacts: list[dict[str, Any]],
        correlation: Any,
        fusion: Any,
        context: Any = None,
    ) -> dict[str, Any]:
        """
        Execute optional reasoning.

        When no reasoning engine is configured, a deterministic
        completed envelope is returned.
        """

        if self.reasoning_engine is None:
            return {
                "reasoning_status": "completed",
                "reasoning_available": False,
                "summary": (
                    self._build_reasoning_summary(
                        correlation,
                        fusion,
                    )
                ),
                "metadata": {
                    "intelligence_reasoning_input": self._intelligence_reasoning_input(fusion, context),
                },
            }

        engine = self.reasoning_engine

        try:
            if hasattr(
                engine,
                "reason",
            ):
                output = engine.reason(
                    artifacts=artifacts,
                    correlation=correlation,
                    fusion=fusion,
                    context=context,
                )

            elif hasattr(
                engine,
                "analyze",
            ):
                output = engine.analyze(
                    artifacts=artifacts,
                    correlation=correlation,
                    fusion=fusion,
                    context=context,
                )

            elif callable(engine):
                output = engine(
                    artifacts,
                    correlation,
                    fusion,
                )

            else:
                output = None

            return {
                "reasoning_status": "completed",
                "reasoning_available": True,
                "output": output,
                "metadata": {
                    "intelligence_reasoning_input": self._intelligence_reasoning_input(fusion, context),
                },
            }

        except TypeError:
            # Compatibility with simple reasoning engines.
            try:
                if hasattr(
                    engine,
                    "reason",
                ):
                    output = engine.reason(
                        artifacts
                    )

                elif hasattr(
                    engine,
                    "analyze",
                ):
                    output = engine.analyze(
                        artifacts
                    )

                elif callable(engine):
                    output = engine(
                        artifacts
                    )

                else:
                    output = None

                return {
                    "reasoning_status": "completed",
                    "reasoning_available": True,
                    "output": output,
                    "metadata": {},
                }

            except Exception as exc:
                return {
                    "reasoning_status": "failed",
                    "reasoning_available": True,
                    "output": None,
                    "error": str(exc),
                    "metadata": {},
                }

        except Exception as exc:
            return {
                "reasoning_status": "failed",
                "reasoning_available": True,
                "output": None,
                "error": str(exc),
                "metadata": {},
            }

    # =========================================================
    # RESULT BUILDING
    # =========================================================

    def _build_success_result(
        self,
        artifacts: list[dict[str, Any]],
        correlation: Any,
        fusion: Any,
        reasoning: dict[str, Any],
        case_id: Optional[str],
        investigation_id: str,
        started_at: str,
        context: Any = None,
    ) -> InvestigationResult:
        """
        Build the canonical successful InvestigationResult.
        """

        correlation_data = self._as_dict(
            correlation
        )

        fusion_data = self._as_dict(
            fusion
        )

        risk = self._extract_risk(
            fusion_data,
            correlation_data,
        )

        confidence = self._extract_confidence(
            fusion_data,
            correlation_data,
        )

        indicators = self._extract_indicators(
            artifacts,
            correlation_data,
        )

        entities = self._extract_list(
            correlation_data,
            "entities",
        )

        relationships = self._extract_list(
            correlation_data,
            "relationships",
        )

        mitre = self._extract_mitre(
            correlation_data,
            fusion_data,
        )

        recommendations = (
            self._extract_recommendations(
                fusion_data,
                reasoning,
            )
        )

        attack_story = (
            fusion_data.get(
                "summary"
            )
            or correlation_data.get(
                "attack_story"
            )
            or reasoning.get(
                "summary"
            )
        )

        intelligence = {
            "correlation": correlation_data,
            "fusion": fusion_data,
            "reasoning": reasoning,
        }

        execution = {
            "orchestrator": (
                "InvestigationOrchestrator"
            ),
            "investigation_id": (
                investigation_id
            ),
            "case_id": case_id,
            "artifact_count": len(
                artifacts
            ),
            "started_at": started_at,
            "completed_at": self._timestamp(),
        }

        metadata = {
            "orchestrator": (
                "InvestigationOrchestrator"
            ),
            "artifact_count": len(
                artifacts
            ),
            "started_at": started_at,
            "completed_at": execution[
                "completed_at"
            ],
            "context_available": (
                context is not None
                or bool(
                    artifacts
                    or case_id
                )
            ),
            "correlation": correlation_data,
            "fusion": fusion_data,
            "execution": execution,
        }

        # The InvestigationResult contract has evolved over time.
        # Build the result using the fields currently supported by
        # the repository contract, then populate compatibility
        # aliases defensively.
        result = InvestigationResult(
            success=True,
            status="completed",
            message=(
                "Investigation completed successfully."
            ),
            error=None,
            investigation_id=(
                investigation_id
            ),
            case_id=case_id,
            artifacts=list(
                artifacts
            ),
            correlation=correlation_data,
            fusion=fusion_data,
            reasoning=reasoning,
            intelligence=intelligence,
            findings=list(
                indicators
            ),
            indicators=list(
                indicators
            ),
            entities=list(
                entities
            ),
            relationships=list(
                relationships
            ),
            mitre=list(
                mitre
            ),
            recommendations=list(
                recommendations
            ),
            attack_story=attack_story,
            execution=execution,
            confidence=confidence,
            risk=risk,
            priority=self._extract_priority(
                fusion_data
            ),
            metadata=metadata,
        )

        return result

    def _build_failure_result(
        self,
        error: str,
        case_id: Optional[str],
        investigation_id: str,
        started_at: str,
        artifacts: Optional[
            list[dict[str, Any]]
        ] = None,
    ) -> InvestigationResult:
        """
        Build a stable failed investigation result.
        """

        completed_at = self._timestamp()

        result = InvestigationResult(
            success=False,
            status="failed",
            message=(
                "Investigation execution failed."
            ),
            error=error,
            investigation_id=(
                investigation_id
            ),
            case_id=case_id,
            artifacts=list(
                artifacts or []
            ),
            findings=[],
            indicators=[],
            entities=[],
            relationships=[],
            mitre=[],
            recommendations=[],
            metadata={
                "orchestrator": (
                    "InvestigationOrchestrator"
                ),
                "started_at": started_at,
                "completed_at": completed_at,
            },
        )

        return result

    # =========================================================
    # NORMALIZATION
    # =========================================================

    @staticmethod
    def _normalize_artifacts(
        artifacts: Optional[
            list[dict[str, Any]]
        ],
    ) -> list[dict[str, Any]]:
        """
        Normalize investigation artifacts.

        The original artifact collection is preserved semantically.
        No synthetic artifacts are inserted here.
        """

        if artifacts is None:
            return []

        normalized: list[
            dict[str, Any]
        ] = []

        for artifact in artifacts:
            if isinstance(
                artifact,
                dict,
            ):
                normalized.append(
                    dict(artifact)
                )
            else:
                normalized.append(
                    {
                        "type": "unknown",
                        "value": artifact,
                    }
                )

        return normalized

    @staticmethod
    def _build_correlation_signals(
        artifacts: list[
            dict[str, Any]
        ],
    ) -> list[
        dict[str, Any]
    ]:
        """
        Build correlation signals.

        Correlation engines in Sentinel DNA operate on a minimum
        two-signal investigation context. When an investigation
        contains only one artifact, a derived context signal is
        added. This does not alter the original artifact list.

        For empty investigations, two deterministic context signals
        are supplied so correlation engines can safely execute.
        """

        signals: list[
            dict[str, Any]
        ] = []

        for artifact in artifacts:
            artifact_type = artifact.get(
                "type",
                artifact.get(
                    "entity_type",
                    "unknown",
                ),
            )

            value = artifact.get(
                "value",
                artifact.get(
                    "ioc",
                    artifact.get(
                        "indicator"
                    ),
                ),
            )

            signals.append(
                {
                    **artifact,
                    "type": artifact_type,
                    "value": value,
                }
            )

        if len(signals) == 0:
            signals.extend(
                [
                    {
                        "type": "investigation_context",
                        "value": "empty",
                        "synthetic": True,
                    },
                    {
                        "type": "investigation_context",
                        "value": "no_artifacts",
                        "synthetic": True,
                    },
                ]
            )

        elif len(signals) == 1:
            original = signals[0]

            signals.append(
                {
                    "type": "investigation_context",
                    "value": original.get(
                        "value"
                    ),
                    "source": (
                        original.get(
                            "type"
                        )
                    ),
                    "synthetic": True,
                }
            )

        return signals

    # =========================================================
    # EXTRACTION HELPERS
    # =========================================================

    @staticmethod
    def _as_dict(
        value: Any,
    ) -> dict[str, Any]:
        """
        Convert a runtime intelligence result into a dictionary.
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
                converted = value.to_dict()

                if isinstance(
                    converted,
                    dict,
                ):
                    return dict(
                        converted
                    )

            except Exception:
                pass

        if hasattr(
            value,
            "__dict__",
        ):
            return {
                key: val
                for key, val in vars(
                    value
                ).items()
                if not key.startswith("_")
            }

        return {}

    @staticmethod
    def _extract_list(
        data: dict[str, Any],
        key: str,
    ) -> list[Any]:
        """
        Extract a normalized list field.
        """

        value = data.get(
            key
        )

        if value is None:
            return []

        if isinstance(
            value,
            list,
        ):
            return list(
                value
            )

        if isinstance(
            value,
            tuple,
        ):
            return list(
                value
            )

        return [value]

    @staticmethod
    def _extract_risk_score(
        correlation: Any,
    ) -> float:
        """
        Extract numeric risk score from correlation output.
        """

        data = (
            InvestigationOrchestrator._as_dict(
                correlation
            )
        )

        value = data.get(
            "risk_score",
            data.get(
                "score",
                0,
            ),
        )

        try:
            return float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return 0.0

    @staticmethod
    def _extract_risk(
        fusion: dict[str, Any],
        correlation: dict[str, Any],
    ) -> str:
        """
        Extract normalized risk.
        """

        threat = fusion.get(
            "threat_assessment",
            {},
        )

        if isinstance(
            threat,
            dict,
        ):
            risk = threat.get(
                "risk"
            )

            if risk:
                return str(
                    risk
                )

        risk = fusion.get(
            "risk"
        )

        if risk:
            return str(
                risk
            )

        risk = correlation.get(
            "risk"
        )

        if risk:
            return str(
                risk
            )

        return "unknown"

    @staticmethod
    def _extract_priority(
        fusion: dict[str, Any],
    ) -> Optional[str]:
        """
        Extract investigation priority.
        """

        threat = fusion.get(
            "threat_assessment",
            {},
        )

        if isinstance(
            threat,
            dict,
        ):
            priority = threat.get(
                "priority"
            )

            if priority is not None:
                return str(
                    priority
                )

        priority = fusion.get(
            "priority"
        )

        if priority is not None:
            return str(
                priority
            )

        return None

    @staticmethod
    def _extract_confidence(
        fusion: dict[str, Any],
        correlation: dict[str, Any],
    ) -> float:
        """
        Extract normalized confidence.
        """

        threat = fusion.get(
            "threat_assessment",
            {},
        )

        if isinstance(
            threat,
            dict,
        ):
            value = threat.get(
                "confidence"
            )

            if value is not None:
                try:
                    return float(
                        value
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    pass

        for source in (
            fusion,
            correlation,
        ):
            value = source.get(
                "confidence"
            )

            if value is not None:
                try:
                    return float(
                        value
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    continue

        return 0.0

    @staticmethod
    def _extract_indicators(
        artifacts: list[
            dict[str, Any]
        ],
        correlation: dict[str, Any],
    ) -> list[Any]:
        """
        Extract investigation indicators.
        """

        indicators = correlation.get(
            "indicators"
        )

        if isinstance(
            indicators,
            list,
        ):
            return list(
                indicators
            )

        return list(
            artifacts
        )

    @staticmethod
    def _extract_mitre(
        correlation: dict[str, Any],
        fusion: dict[str, Any],
    ) -> list[Any]:
        """
        Extract MITRE ATT&CK mappings.
        """

        for source in (
            correlation,
            fusion,
        ):
            value = source.get(
                "mitre"
            )

            if isinstance(
                value,
                list,
            ):
                return list(
                    value
                )

            threat = source.get(
                "threat_assessment"
            )

            if isinstance(
                threat,
                dict,
            ):
                value = threat.get(
                    "mitre"
                )

                if isinstance(
                    value,
                    list,
                ):
                    return list(
                        value
                    )

        return []

    @staticmethod
    def _extract_recommendations(
        fusion: dict[str, Any],
        reasoning: dict[str, Any],
    ) -> list[Any]:
        """
        Extract response recommendations.
        """

        for source in (
            fusion,
            reasoning,
        ):
            value = source.get(
                "recommendations"
            )

            if isinstance(
                value,
                list,
            ):
                return list(
                    value
                )

        return []

    @staticmethod
    def _build_reasoning_summary(
        correlation: Any,
        fusion: Any,
    ) -> str:
        """
        Build a deterministic reasoning summary.
        """

        correlation_data = (
            InvestigationOrchestrator._as_dict(
                correlation
            )
        )

        fusion_data = (
            InvestigationOrchestrator._as_dict(
                fusion
            )
        )

        return (
            fusion_data.get(
                "summary"
            )
            or correlation_data.get(
                "attack_story"
            )
            or (
                "Investigation intelligence "
                "processed."
            )
        )

    @staticmethod
    def _intelligence_reasoning_input(fusion: Any, context: Any = None) -> dict[str, Any]:
        """Expose intelligence as evidence categories, never as decision authority."""
        data = InvestigationOrchestrator._as_dict(fusion)
        governance = IntelligenceDecisionGovernance().evaluate(fusion, context=context)
        status = str(data.get("status", "NO_INTELLIGENCE")).upper()
        if status in {"NO_INTELLIGENCE", "UNKNOWN"}:
            category = "NO_INTELLIGENCE"
        elif status == "CONFLICTED":
            category = "PROVIDER_DISAGREEMENT"
        else:
            category = "FUSED_ASSESSMENT"
        return {
            "category": category,
            "status": status,
            "reputation": data.get("aggregate_reputation", data.get("risk", "unknown")),
            "confidence": data.get("aggregate_confidence", data.get("confidence")),
            "freshness": {
                "stale_providers": data.get("stale_providers", []),
                "supporting_providers": data.get("supporting_providers", []),
                "conflicting_providers": data.get("conflicting_providers", []),
            },
            "stale_providers": data.get("stale_providers", []),
            "supporting_providers": data.get("supporting_providers", []),
            "conflicting_providers": data.get("conflicting_providers", []),
            "provenance": data.get("provenance", []),
            "explanation": data.get("explanation", "External intelligence was unavailable or inconclusive."),
            "policy_version": data.get("policy_version"),
            "governance": governance.to_dict(),
        }

    # =========================================================
    # IDENTIFIERS / TIME
    # =========================================================

    @staticmethod
    def _generate_investigation_id(
        case_id: Optional[str],
    ) -> str:
        """
        Generate a globally useful investigation identifier.
        """

        prefix = (
            case_id
            if case_id
            else "INVESTIGATION"
        )

        timestamp = datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%d%H%M%S%f"
        )

        return (
            f"{prefix}-{timestamp}"
        )

    @staticmethod
    def _timestamp() -> str:
        """
        Return an ISO-8601 UTC timestamp.
        """

        return datetime.now(
            timezone.utc
        ).isoformat()


__all__ = [
    "InvestigationOrchestrator",
]
