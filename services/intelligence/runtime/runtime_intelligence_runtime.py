"""
Runtime Intelligence Runtime

Top-level lifecycle and execution boundary for
Sentinel DNA runtime intelligence capabilities.

The runtime intentionally remains thin. Request
normalization belongs to the facade/controller layer.
"""

from .runtime_intelligence_facade import (
    RuntimeIntelligenceFacade,
)


class RuntimeIntelligenceRuntime:
    """
    Top-level runtime intelligence lifecycle component.

    Responsibilities:

    - runtime lifecycle
    - capability registration
    - execution delegation
    - health/status reporting

    The runtime does not construct investigation
    contexts itself. That responsibility belongs to
    RuntimeIntelligenceFacade and
    RuntimeIntelligenceController.
    """

    def __init__(
        self,
        facade=None,
    ):
        self.facade = (
            facade
            if facade is not None
            else RuntimeIntelligenceFacade()
        )

        self.running = False

        self.requests = 0

        self.executions = 0

        self.failures = 0

    # =========================================================
    # LIFECYCLE
    # =========================================================

    def start(
        self,
    ):
        """
        Start the runtime.
        """

        self.running = True

        return True

    def stop(
        self,
    ):
        """
        Stop the runtime.
        """

        self.running = False

        return True

    # =========================================================
    # REGISTRATION
    # =========================================================

    def register(
        self,
        capability,
        handler,
    ):
        """
        Register an intelligence capability.

        Registration is delegated to the facade so that
        the runtime does not duplicate registry logic.
        """

        return self.facade.register_capability(
            capability,
            handler,
        )

    # =========================================================
    # EXECUTION
    # =========================================================

    def execute(
        self,
        capability,
        investigation_id=None,
        payload=None,
        case_id=None,
        metadata=None,
    ):
        """
        Execute an intelligence capability.

        Public contract:

            runtime.execute(
                "investigation",
                "INC-001",
            )

        The second positional argument is explicitly the
        investigation identifier.

        It is passed to the facade using the named
        ``investigation_id`` parameter to prevent positional
        argument drift between runtime layers.
        """

        if not self.running:
            self.start()

        self.requests += 1

        result = self.facade.execute(
            capability=capability,
            investigation_id=investigation_id,
            payload=payload,
            case_id=case_id,
            metadata=metadata,
        )

        if not isinstance(
            result,
            dict,
        ):
            self.failures += 1

            return {
                "success": False,
                "result": None,
                "error":
                    "Runtime intelligence facade returned "
                    "an invalid response.",
                "investigation_id":
                    investigation_id,
                "case_id":
                    case_id,
            }

        if result.get(
            "success"
        ) is True:

            self.executions += 1

        else:

            self.failures += 1

        return result

    # =========================================================
    # HEALTH
    # =========================================================

    def health(
        self,
    ):
        """
        Return runtime health information.

        Keep this intentionally compatible with the
        existing runtime intelligence health contract.
        """

        facade_status = self.facade.status()

        return {
            "healthy": True,

            "running":
                self.running,

            "intelligence":
                True,

            "components":
                [],

            "requests":
                self.requests,

            "executions":
                self.executions,

            "failures":
                self.failures,

            "facade":
                facade_status,
        }

    # =========================================================
    # STATUS
    # =========================================================

    def status(
        self,
    ):
        """
        Alias for health().
        """

        return self.health()