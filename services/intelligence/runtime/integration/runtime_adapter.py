"""
Sentinel DNA - Runtime Adapter

Normalizes external security events
into runtime service requests.
"""

from __future__ import annotations

from typing import Any


from services.intelligence.runtime.api.runtime_service import (
    RuntimeService,
)



class RuntimeAdapter:
    """
    Integration adapter between
    external security systems and
    Sentinel DNA runtime.
    """


    def __init__(
        self,
        runtime_service: RuntimeService | None = None,
    ):

        self.runtime_service = (
            runtime_service
            or RuntimeService()
        )



    def process_alert(
        self,
        alert: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert external alert into
        investigation request.
        """


        normalized = (
            self.normalize_alert(
                alert
            )
        )


        return self.runtime_service.start_investigation(

            case_id=
                normalized["case_id"],

            evidence=
                normalized["evidence"],

        )



    def normalize_alert(
        self,
        alert: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert external alert schema
        into Sentinel DNA evidence format.
        """


        case_id = (
            alert.get(
                "case_id"
            )
            or
            alert.get(
                "id"
            )
            or
            "UNKNOWN"
        )


        evidence = []


        if alert.get("indicator"):

            evidence.append(

                {

                    "type":
                        "ioc",

                    "value":
                        alert["indicator"],

                    "severity":
                        alert.get(
                            "severity",
                            "unknown",
                        ),

                }

            )


        if alert.get("source"):

            evidence.append(

                {

                    "type":
                        "source",

                    "value":
                        alert["source"],

                }

            )


        return {

            "case_id":
                case_id,

            "evidence":
                evidence,

        }