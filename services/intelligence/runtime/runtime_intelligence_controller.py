"""
Runtime Intelligence Controller

Runtime API facade.

Responsible for:

- receiving execution requests
- invoking intelligence service
- serializing responses
"""

from typing import Any



class RuntimeIntelligenceController:
    """
    Controller layer for runtime intelligence.
    """


    def __init__(
        self,
        intelligence_service,
    ):

        self.service = (
            intelligence_service
        )



    def execute(
        self,
        signals: list[dict[str, Any]],
        case_id: str | None = None,
    ):

        """
        Execute intelligence investigation.
        """


        result = (
            self.service.investigate(
                signals,
                case_id,
            )
        )


        return self._serialize(
            result
        )



    def health(
        self,
    ):

        return {

            "component":
                "runtime_intelligence_controller",

            "status":
                "ready",

        }



    def _serialize(
        self,
        result,
    ):

        if hasattr(
            result,
            "to_dict",
        ):

            return result.to_dict()


        return {

            "success":
                False,

            "error":
                "Invalid intelligence result",

        }