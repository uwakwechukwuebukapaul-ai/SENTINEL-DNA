"""
Runtime Intelligence Facade

Public application-facing facade for runtime intelligence.

The facade provides a stable execution contract between
the top-level Runtime Intelligence Runtime and the
Runtime Intelligence Controller.
"""

from .runtime_intelligence_controller import (
    RuntimeIntelligenceController,
)


class RuntimeIntelligenceFacade:
    """
    Stable public facade over RuntimeIntelligenceController.
    """

    def __init__(
        self,
        controller=None,
    ):
        self.controller = (
            controller
            if controller is not None
            else RuntimeIntelligenceController()
        )

        self.requests = 0

        self.executions = 0

        self.failures = 0

    # =========================================================
    # REGISTRATION
    # =========================================================

    def register_capability(
        self,
        capability,
        handler,
    ):
        """
        Register an intelligence capability.
        """

        return self.controller.register(
            capability,
            handler,
        )

    def register(
        self,
        capability,
        handler,
    ):
        """
        Compatibility alias for register_capability().
        """

        return self.register_capability(
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
        Execute a runtime intelligence capability.

        Supported public form:

            facade.execute(
                "investigation",
                "INC-001",
            )

        Keyword form:

            facade.execute(
                capability="investigation",
                investigation_id="INC-001",
            )

        Both forms normalize to the controller request
        contract.
        """

        self.requests += 1

        request = {
            "capability":
                capability,

            "investigation_id":
                investigation_id,

            "case_id":
                case_id,

            "payload":
                payload,

            "metadata":
                (
                    dict(metadata)
                    if isinstance(
                        metadata,
                        dict,
                    )
                    else {}
                ),
        }

        result = self.controller.investigate(
            request
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
                    "Runtime intelligence controller "
                    "returned an invalid response.",

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
    # STATUS
    # =========================================================

    def status(
        self,
    ):
        """
        Return facade status.
        """

        controller_status = (
            self.controller.status()
        )

        return {
            "healthy": True,

            "requests":
                self.requests,

            "executions":
                self.executions,

            "failures":
                self.failures,

            "controller":
                controller_status,
        }