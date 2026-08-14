"""
Sentinel DNA Investigation Context.

Provides a stable investigation-scoped data container
shared across intelligence engines.

The context prevents every intelligence component from
independently rebuilding the same investigation state.
"""


class InvestigationContext:
    """
    Investigation-scoped intelligence context.
    """

    def __init__(
        self,
        investigation_id,
        case_id=None,
        alert=None,
        artifacts=None,
        indicators=None,
        entities=None,
        timeline=None,
        notes=None,
        correlation=None,
    ):
        self.investigation_id = (
            investigation_id
        )

        self.case_id = (
            case_id
            or investigation_id
        )

        self.alert = (
            alert or {}
        )

        self.artifacts = list(
            artifacts or []
        )

        self.indicators = list(
            indicators or []
        )

        self.entities = list(
            entities or []
        )

        self.timeline = list(
            timeline or []
        )

        self.notes = list(
            notes or []
        )

        self.correlation = correlation

        # Compatibility aliases used by reasoning engines.
        self.evidence = self.artifacts
        self.iocs = self.indicators

    def add_evidence(self, evidence):
        self.evidence.append(evidence)

    def add_ioc(self, ioc):
        self.iocs.append(ioc)

    def add_timeline_event(self, event):
        self.timeline.append(event)

    # --------------------------------------------------------
    # Indicator management
    # --------------------------------------------------------

    def add_indicator(
        self,
        indicator,
    ):
        self.indicators.append(
            indicator
        )

    # --------------------------------------------------------
    # Entity management
    # --------------------------------------------------------

    def add_entity(
        self,
        entity,
    ):
        self.entities.append(
            entity
        )

    # --------------------------------------------------------
    # Artifact management
    # --------------------------------------------------------

    def add_artifact(
        self,
        artifact,
    ):
        self.artifacts.append(
            artifact
        )

    # --------------------------------------------------------
    # Correlation
    # --------------------------------------------------------

    def set_correlation(
        self,
        result,
    ):
        self.correlation = result

    # --------------------------------------------------------
    # Serialization
    # --------------------------------------------------------

    def to_dict(self):

        correlation = self.correlation

        if hasattr(
            correlation,
            "to_dict",
        ):
            correlation = (
                correlation.to_dict()
            )

        return {
            "investigation_id":
                self.investigation_id,

            "case_id":
                self.case_id,

            "alert":
                self.alert,

            "artifacts":
                self.artifacts,

            "evidence":
                self.evidence,

            "indicators":
                self.indicators,

            "iocs":
                self.iocs,

            "entities":
                self.entities,

            "timeline":
                self.timeline,

            "notes":
                self.notes,

            "correlation":
                correlation,
        }

    def snapshot(self):
        return self.to_dict()


def load_investigation_context(
    case_id,
    alert=None,
    artifacts=None,
    indicators=None,
    entities=None,
    timeline=None,
    notes=None,
):
    """
    Construct a fresh investigation context.

    Persistence/database loading can be layered underneath
    this function later without changing consumers.
    """

    return InvestigationContext(
        investigation_id=case_id,
        case_id=case_id,
        alert=alert,
        artifacts=artifacts,
        indicators=indicators,
        entities=entities,
        timeline=timeline,
        notes=notes,
    )
