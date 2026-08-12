from dataclasses import dataclass, field, asdict
from typing import Any

from sentinel_dna.case_management.models import Case
from sentinel_dna.evidence.models import Evidence
from sentinel_dna.investigation.trace import InvestigationTrace
from sentinel_dna.investigation.graph import InvestigationGraph


@dataclass
class InvestigationContext:
    """
    Shared investigation state container.

    The context is created once per investigation and passed
    through the complete AI Investigator workflow.

    Responsibilities:

    - case state
    - evidence state
    - IOC intelligence
    - threat analysis
    - reasoning state
    - decision intelligence
    - audit trace
    - replay/provenance graph

    This object acts as the single source of truth
    during an investigation execution.
    """

    case_id: str
    alert: dict[str, Any]

    # Case information
    case: Case | None = None

    # Evidence layer
    evidence_items: list[Evidence] = field(
        default_factory=list
    )

    # IOC layer
    iocs: list[str] = field(
        default_factory=list
    )

    intelligence: dict[str, Any] = field(
        default_factory=dict
    )

    correlations: list[dict[str, Any]] = field(
        default_factory=list
    )

    timeline: list[dict[str, Any]] = field(
        default_factory=list
    )

    # MITRE ATT&CK mapping
    mitre_attack: list[dict[str, str]] = field(
        default_factory=list
    )

    # Threat analysis
    threat_classification: dict[str, Any] = field(
        default_factory=dict
    )

    risk: Any | None = None

    confidence: dict[str, Any] = field(
        default_factory=dict
    )

    # AI reasoning layer
    reasoning: dict[str, Any] = field(
        default_factory=dict
    )

    # Decision intelligence layer
    decision_intelligence: dict[str, Any] = field(
        default_factory=dict
    )

    recommendations: list[str] = field(
        default_factory=list
    )

    # Reporting
    report: dict[str, Any] = field(
        default_factory=dict
    )

    # Runtime execution
    task_results: list[dict[str, Any]] = field(
        default_factory=list
    )

    # Audit and governance
    audit_trail: list[dict[str, Any]] = field(
        default_factory=list
    )

    errors: list[dict[str, Any]] = field(
        default_factory=list
    )

    uncertainties: list[str] = field(
        default_factory=list
    )

    # Investigation lifecycle trace
    trace: InvestigationTrace | None = None


    # =====================================
    # Investigation Graph Layer
    # =====================================

    graph: InvestigationGraph = field(
        default_factory=InvestigationGraph
    )


    # =====================================
    # Replay / Snapshot Metadata
    # =====================================

    snapshot_metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def add_uncertainty(
        self,
        message: str,
    ) -> None:
        """
        Add investigation uncertainty.
        """

        if message not in self.uncertainties:
            self.uncertainties.append(
                message
            )


    def graph_snapshot(
        self,
    ) -> dict[str, Any]:
        """
        Return investigation graph state.

        Used by:
        - replay engine
        - provenance tracking
        - analyst audit views
        """

        return self.graph.to_dict()


    def export_state(
        self,
    ) -> dict[str, Any]:
        """
        Export serializable investigation state.

        Useful for:
        - persistence
        - replay
        - debugging
        """

        return {
            "case_id": self.case_id,
            "alert": self.alert,
            "iocs": self.iocs,
            "intelligence": self.intelligence,
            "correlations": self.correlations,
            "timeline": self.timeline,
            "mitre_attack": self.mitre_attack,
            "threat_classification": (
                self.threat_classification
            ),
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "decision_intelligence": (
                self.decision_intelligence
            ),
            "recommendations": self.recommendations,
            "task_results": self.task_results,
            "audit_trail": self.audit_trail,
            "errors": self.errors,
            "uncertainties": self.uncertainties,
            "graph": self.graph_snapshot(),
            "snapshot_metadata": (
                self.snapshot_metadata
            ),
        }