"""
Runtime Intelligence Context

Shared investigation state passed between
runtime intelligence capabilities.
"""


class RuntimeIntelligenceContext:
    """
    Shared runtime investigation context.

    Provides a stable contract for:
    - Runtime controller
    - Runtime facade
    - Runtime pipeline
    - Intelligence services
    - Execution engines
    """


    def __init__(
        self,
        investigation_id=None,
        case_id=None,
        metadata=None,
        signals=None,
        evidence=None,
        iocs=None,
        mitre=None,
        events=None,
        **kwargs,
    ):

        self.investigation_id = investigation_id

        self.case_id = (
            case_id
            or investigation_id
        )

        self.metadata = metadata or {}

        self.signals = signals or []

        self.evidence = evidence or []

        self.iocs = iocs or []

        self.mitre = mitre or []

        self.events = events or []

        self._status = "initialized"



    # ---------------------------------
    # Evidence
    # ---------------------------------

    def add_evidence(
        self,
        evidence,
    ):

        self.evidence.append(
            evidence
        )

        return True



    # ---------------------------------
    # IOC
    # ---------------------------------

    def add_ioc(
        self,
        ioc,
    ):

        self.iocs.append(
            ioc
        )

        return True



    # ---------------------------------
    # MITRE
    # ---------------------------------

    def add_mitre(
        self,
        technique,
    ):

        self.mitre.append(
            technique
        )

        return True



    # ---------------------------------
    # Signals
    # ---------------------------------

    def add_signal(
        self,
        signal,
    ):

        self.signals.append(
            signal
        )

        return True



    # ---------------------------------
    # Events
    # ---------------------------------

    def add_event(
        self,
        event,
    ):

        self.events.append(
            event
        )

        return True



    # ---------------------------------
    # Metadata
    # ---------------------------------

    def update_metadata(
        self,
        key,
        value=None,
    ):

        if isinstance(
            key,
            dict,
        ):

            self.metadata.update(
                key
            )

        else:

            self.metadata[key] = value


        return True



    # ---------------------------------
    # Status
    # ---------------------------------

    def update_status(
        self,
        status,
    ):

        self._status = status

        return True



    def status(
        self,
    ):

        return {

            "investigation_id":
                self.investigation_id,

            "case_id":
                self.case_id,

            "status":
                self._status,

            "evidence_count":
                len(
                    self.evidence
                ),

            "ioc_count":
                len(
                    self.iocs
                ),

            "mitre_count":
                len(
                    self.mitre
                ),

            "signal_count":
                len(
                    self.signals
                ),

            "event_count":
                len(
                    self.events
                ),

            "metadata":
                self.metadata,

        }



    # ---------------------------------
    # Compatibility Helpers
    # ---------------------------------

    def get(
        self,
        key,
        default=None,
    ):

        if hasattr(
            self,
            key,
        ):

            return getattr(
                self,
                key,
            )

        return self.metadata.get(
            key,
            default,
        )



    def to_dict(
        self,
    ):

        return {

            "investigation_id":
                self.investigation_id,

            "case_id":
                self.case_id,

            "status":
                self._status,

            "metadata":
                self.metadata,

            "signals":
                self.signals,

            "evidence":
                self.evidence,

            "iocs":
                self.iocs,

            "mitre":
                self.mitre,

            "events":
                self.events,

        }



    def __repr__(
        self,
    ):

        return (
            "RuntimeIntelligenceContext("
            f"investigation_id={self.investigation_id!r}, "
            f"status={self._status!r})"
        )