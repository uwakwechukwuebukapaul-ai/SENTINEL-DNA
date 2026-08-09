"""
Runtime Intelligence Context

Shared state container for runtime intelligence execution.

Stores:

- signals
- provider intelligence
- correlations
- fusion outputs
- decisions
- execution metadata
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


    decisions: list[Any] = field(
        default_factory=list
    )


    timeline: list[dict[str, Any]] = field(
        default_factory=list
    )


    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    status: str = "initialized"



    def add_signal(
        self,
        signal: dict[str, Any],
    ):

        self.signals.append(
            signal
        )



    def add_record(
        self,
        record: Any,
    ):

        self.intelligence_records.append(
            record
        )



    def add_entity(
        self,
        entity: Any,
    ):

        self.entities.append(
            entity
        )



    def add_correlation(
        self,
        correlation: Any,
    ):

        self.correlations.append(
            correlation
        )



    def add_fusion_result(
        self,
        result: Any,
    ):

        self.fusion_results.append(
            result
        )



    def add_decision(
        self,
        decision: Any,
    ):

        self.decisions.append(
            decision
        )



    def add_event(
        self,
        event: dict[str, Any],
    ):

        self.timeline.append(
            event
        )



    def update_status(
        self,
        status: str,
    ):

        self.status = status



    def summary(
        self,
    ):

        return {

            "case_id":
                self.case_id,

            "signals":
                len(self.signals),

            "records":
                len(self.intelligence_records),

            "entities":
                len(self.entities),

            "correlations":
                len(self.correlations),

            "fusion_results":
                len(self.fusion_results),

            "decisions":
                len(self.decisions),

            "status":
                self.status,

        }