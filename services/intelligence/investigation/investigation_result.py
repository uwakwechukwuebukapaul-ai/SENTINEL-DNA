"""
Sentinel DNA Investigation Result

Unified investigation execution response contract.

This contract is shared by:

- Investigation Orchestrator
- Investigation Pipeline
- Investigation Service
- Investigation Coordinator
- Investigation Intelligence
- Runtime execution layers
- Correlation layer
- Threat fusion layer
- Reasoning layer
- Reporting layer
- Investigation history

The object supports both:

    result.success

and:

    result["success"]

The contract intentionally provides compatibility fields and
helpers for older and newer investigation execution components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class InvestigationResult:
    """
    Standard Sentinel DNA investigation execution result.

    This is the canonical result envelope for the investigation
    execution layer.

    Supports:

    - Attribute-style access
    - Dictionary-style access
    - Success/failure factories
    - Metadata mutation
    - Intelligence result attachment
    - Investigation findings
    - IOC/indicator collections
    - Backward compatibility
    """

    # =========================================================
    # EXECUTION STATE
    # =========================================================

    success: bool = False

    status: str = "failed"

    message: Optional[str] = None

    error: Optional[str] = None

    # =========================================================
    # CORRELATION IDENTIFIERS
    # =========================================================

    investigation_id: Optional[str] = None

    case_id: Optional[str] = None

    execution_id: Optional[str] = None

    # =========================================================
    # INVESTIGATION INPUT
    # =========================================================

    artifacts: list[Any] = field(
        default_factory=list
    )

    # =========================================================
    # INTELLIGENCE RESULTS
    # =========================================================

    correlation: Any = None

    fusion: Any = None

    reasoning: Any = None

    intelligence: Any = None

    # =========================================================
    # INVESTIGATION FINDINGS
    # =========================================================

    findings: list[Any] = field(
        default_factory=list
    )

    indicators: list[Any] = field(
        default_factory=list
    )

    entities: list[Any] = field(
        default_factory=list
    )

    relationships: list[Any] = field(
        default_factory=list
    )

    mitre: list[Any] = field(
        default_factory=list
    )

    recommendations: list[Any] = field(
        default_factory=list
    )

    attack_story: Optional[str] = None

    # =========================================================
    # EXECUTION / WORKFLOW RESULTS
    # =========================================================

    execution: Any = None

    workflow: Any = None

    report: Any = None

    # =========================================================
    # GENERIC RESULT PAYLOADS
    # =========================================================

    output: Any = None

    result: Any = None

    data: Any = None

    # =========================================================
    # INTELLIGENCE METADATA
    # =========================================================

    confidence: float = 0.0

    risk: Optional[str] = None

    priority: Optional[str] = None

    # =========================================================
    # METADATA
    # =========================================================

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # =========================================================
    # SUCCESS FACTORIES
    # =========================================================

    @classmethod
    def ok(
        cls,
        result: Any = None,
        message: Optional[str] = None,
        **kwargs: Any,
    ) -> "InvestigationResult":
        """
        Create a successful investigation result.

        Explicit caller values always take precedence.
        """

        values = dict(kwargs)

        values.setdefault(
            "success",
            True,
        )

        values.setdefault(
            "status",
            "completed",
        )

        values.setdefault(
            "message",
            message,
        )

        values.setdefault(
            "output",
            result,
        )

        values.setdefault(
            "result",
            result,
        )

        values.setdefault(
            "data",
            result,
        )

        return cls(
            **values
        )

    @classmethod
    def success_result(
        cls,
        result: Any = None,
        message: Optional[str] = None,
        **kwargs: Any,
    ) -> "InvestigationResult":
        """
        Compatibility alias for ok().
        """

        return cls.ok(
            result=result,
            message=message,
            **kwargs,
        )

    # =========================================================
    # FAILURE FACTORIES
    # =========================================================

    @classmethod
    def fail(
        cls,
        error: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs: Any,
    ) -> "InvestigationResult":
        """
        Create a failed investigation result.
        """

        values = dict(kwargs)

        values.setdefault(
            "success",
            False,
        )

        values.setdefault(
            "status",
            "failed",
        )

        values.setdefault(
            "message",
            message,
        )

        values.setdefault(
            "error",
            error,
        )

        return cls(
            **values
        )

    @classmethod
    def failure(
        cls,
        error: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs: Any,
    ) -> "InvestigationResult":
        """
        Compatibility factory for fail().
        """

        return cls.fail(
            error=error,
            message=message,
            **kwargs,
        )

    @classmethod
    def failure_result(
        cls,
        error: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs: Any,
    ) -> "InvestigationResult":
        """
        Compatibility alias for failure().
        """

        return cls.failure(
            error=error,
            message=message,
            **kwargs,
        )

    # =========================================================
    # STATE HELPERS
    # =========================================================

    @property
    def failed(self) -> bool:
        """
        True when the investigation did not succeed.
        """

        return self.success is False

    @property
    def completed(self) -> bool:
        """
        True when the investigation completed successfully.
        """

        return (
            self.success is True
            and self.status == "completed"
        )

    @property
    def successful(self) -> bool:
        """
        Compatibility alias for success.
        """

        return self.success is True

    # =========================================================
    # METADATA HELPERS
    # =========================================================

    def add_metadata(
        self,
        key: str,
        value: Any,
    ) -> "InvestigationResult":
        """
        Add or replace one metadata value.
        """

        self.metadata[key] = value

        return self

    def update_metadata(
        self,
        values: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> "InvestigationResult":
        """
        Update multiple metadata values.

        Supports:

            result.update_metadata(
                {"key": "value"}
            )

        and:

            result.update_metadata(
                key="value"
            )
        """

        if values:
            self.metadata.update(
                values
            )

        if kwargs:
            self.metadata.update(
                kwargs
            )

        return self

    # =========================================================
    # RESULT ATTACHMENT HELPERS
    # =========================================================

    def set_correlation(
        self,
        correlation: Any,
    ) -> "InvestigationResult":
        """
        Attach correlation output.
        """

        self.correlation = correlation

        return self

    def set_fusion(
        self,
        fusion: Any,
    ) -> "InvestigationResult":
        """
        Attach threat-fusion output.
        """

        self.fusion = fusion

        return self

    def set_reasoning(
        self,
        reasoning: Any,
    ) -> "InvestigationResult":
        """
        Attach reasoning output.
        """

        self.reasoning = reasoning

        return self

    def set_intelligence(
        self,
        intelligence: Any,
    ) -> "InvestigationResult":
        """
        Attach aggregate intelligence output.
        """

        self.intelligence = intelligence

        return self

    def set_report(
        self,
        report: Any,
    ) -> "InvestigationResult":
        """
        Attach investigation report.
        """

        self.report = report

        return self

    def set_findings(
        self,
        findings: Any,
    ) -> "InvestigationResult":
        """
        Attach investigation findings.
        """

        self.findings = self._normalize_list(
            findings
        )

        return self

    def set_indicators(
        self,
        indicators: Any,
    ) -> "InvestigationResult":
        """
        Attach investigation indicators / IOCs.
        """

        self.indicators = self._normalize_list(
            indicators
        )

        return self

    def set_recommendations(
        self,
        recommendations: Any,
    ) -> "InvestigationResult":
        """
        Attach investigation recommendations.
        """

        self.recommendations = (
            self._normalize_list(
                recommendations
            )
        )

        return self

    # =========================================================
    # NORMALIZATION
    # =========================================================

    @staticmethod
    def _normalize_list(
        value: Any,
    ) -> list[Any]:
        """
        Normalize an arbitrary value into a list.
        """

        if value is None:
            return []

        if isinstance(
            value,
            list,
        ):
            return list(value)

        if isinstance(
            value,
            tuple,
        ):
            return list(value)

        return [value]

    # =========================================================
    # DICTIONARY COMPATIBILITY
    # =========================================================

    def __getitem__(
        self,
        key: str,
    ) -> Any:
        """
        Dictionary-style access.

        Examples:

            result["success"]
            result["correlation"]
            result["fusion"]
            result["reasoning"]
            result["indicators"]
            result["findings"]
        """

        return self.to_dict()[key]

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Dictionary-style get().
        """

        return self.to_dict().get(
            key,
            default,
        )

    def keys(self):
        """
        Dictionary compatibility.
        """

        return self.to_dict().keys()

    def values(self):
        """
        Dictionary compatibility.
        """

        return self.to_dict().values()

    def items(self):
        """
        Dictionary compatibility.
        """

        return self.to_dict().items()

    def __contains__(
        self,
        key: str,
    ) -> bool:
        """
        Dictionary compatibility.
        """

        return key in self.to_dict()

    # =========================================================
    # SERIALIZATION
    # =========================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the investigation result into an
        API-friendly dictionary.

        Runtime objects are intentionally preserved here.
        Higher-level API serializers may normalize them
        at their transport boundaries.
        """

        return {
            # -------------------------------------------------
            # Execution state
            # -------------------------------------------------

            "success":
                self.success,

            "status":
                self.status,

            "message":
                self.message,

            "error":
                self.error,

            # -------------------------------------------------
            # Identifiers
            # -------------------------------------------------

            "investigation_id":
                self.investigation_id,

            "case_id":
                self.case_id,

            "execution_id":
                self.execution_id,

            # -------------------------------------------------
            # Input
            # -------------------------------------------------

            "artifacts":
                list(
                    self.artifacts
                ),

            # -------------------------------------------------
            # Intelligence
            # -------------------------------------------------

            "correlation":
                self.correlation,

            "fusion":
                self.fusion,

            "reasoning":
                self.reasoning,

            "intelligence":
                self.intelligence,

            # -------------------------------------------------
            # Findings
            # -------------------------------------------------

            "findings":
                list(
                    self.findings
                ),

            "indicators":
                list(
                    self.indicators
                ),

            "entities":
                list(
                    self.entities
                ),

            "relationships":
                list(
                    self.relationships
                ),

            "mitre":
                list(
                    self.mitre
                ),

            "recommendations":
                list(
                    self.recommendations
                ),

            "attack_story":
                self.attack_story,

            # -------------------------------------------------
            # Execution
            # -------------------------------------------------

            "execution":
                self.execution,

            "workflow":
                self.workflow,

            "report":
                self.report,

            # -------------------------------------------------
            # Generic payloads
            # -------------------------------------------------

            "output":
                self.output,

            "result":
                self.result,

            "data":
                self.data,

            # -------------------------------------------------
            # Intelligence metadata
            # -------------------------------------------------

            "confidence":
                self.confidence,

            "risk":
                self.risk,

            "priority":
                self.priority,

            # -------------------------------------------------
            # Metadata
            # -------------------------------------------------

            "metadata":
                dict(
                    self.metadata
                ),
        }

    # =========================================================
    # BOOLEAN COMPATIBILITY
    # =========================================================

    def is_success(
        self,
    ) -> bool:
        """
        Return True when the investigation succeeded.
        """

        return self.success is True

    def is_failed(
        self,
    ) -> bool:
        """
        Return True when the investigation failed.
        """

        return self.failed

    def __bool__(
        self,
    ) -> bool:
        """
        Allow:

            if result:
                ...
        """

        return self.success is True


__all__ = [
    "InvestigationResult",
]