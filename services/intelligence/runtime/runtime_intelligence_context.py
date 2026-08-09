"""
Runtime Intelligence Context

Shared investigation intelligence state.
Prevents repeated provider and correlation execution.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeIntelligenceContext:
    """
    Runtime intelligence execution context.
    """

    case_id: str | None = None

    signals: list[dict[str, Any]] = field(
        default_factory=list
    )

    intelligence_records: list[Any] = field(
        default_factory=list
    )

    entities: list[Any] = field(
        default_factory=list
    )

    correlations: list[Any] = field(
        default_factory=list
    )

    fusion_results: list[Any] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def add_signal(
        self,
        signal: dict[str, Any],
    ):
        self.signals.append(signal)


    def add_record(
        self,
        record: Any,
    ):
        self.intelligence_records.append(record)


    def add_correlation(
        self,
        correlation: Any,
    ):
        self.correlations.append(correlation)


    def add_fusion_result(
        self,
        result: Any,
    ):
        self.fusion_results.append(result)