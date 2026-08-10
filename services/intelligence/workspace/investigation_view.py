"""
Sentinel DNA Investigation View

Creates analyst-readable investigation summaries.

Consumes:

- InvestigationResult
- InvestigationReport
- Correlation output
- Threat fusion output
- Reasoning output
"""

from __future__ import annotations

from typing import Any


class InvestigationView:
    """
    Analyst investigation summary builder.
    """


    def build(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build investigation analyst view.
        """

        correlation = self._normalize(
            investigation.get(
                "correlation"
            )
        )

        fusion = self._normalize(
            investigation.get(
                "fusion"
            )
        )

        reasoning = self._normalize(
            investigation.get(
                "reasoning"
            )
        )


        threat = self._normalize(
            fusion.get(
                "threat_assessment"
            )
        )


        return {

            "case_id":
                investigation.get(
                    "case_id"
                ),

            "investigation_id":
                investigation.get(
                    "investigation_id"
                ),


            "risk":
                (
                    investigation.get(
                        "risk"
                    )
                    or threat.get(
                        "risk"
                    )
                    or correlation.get(
                        "risk"
                    )
                    or "unknown"
                ),


            "severity":
                (
                    investigation.get(
                        "severity"
                    )
                    or threat.get(
                        "priority"
                    )
                    or "unknown"
                ),


            "confidence":
                (
                    investigation.get(
                        "confidence"
                    )
                    or correlation.get(
                        "confidence"
                    )
                    or threat.get(
                        "confidence"
                    )
                    or 0.0
                ),


            "attack_story":
                (
                    investigation.get(
                        "attack_story"
                    )
                    or fusion.get(
                        "summary"
                    )
                    or correlation.get(
                        "attack_story"
                    )
                    or reasoning.get(
                        "summary"
                    )
                    or ""
                ),


            "entities":
                correlation.get(
                    "entities",
                    [],
                ),


            "relationships":
                correlation.get(
                    "relationships",
                    [],
                ),


            "mitre":
                (
                    correlation.get(
                        "mitre"
                    )
                    or fusion.get(
                        "mitre"
                    )
                    or []
                ),


            "recommendations":
                (
                    fusion.get(
                        "recommendations"
                    )
                    or reasoning.get(
                        "recommendations"
                    )
                    or []
                ),


            "status":
                investigation.get(
                    "status",
                    "completed",
                ),
        }



    @staticmethod
    def _normalize(
        value: Any,
    ) -> dict[str, Any]:
        """
        Normalize nested intelligence objects.
        """

        if value is None:
            return {}


        if isinstance(
            value,
            dict,
        ):
            return dict(value)


        if hasattr(
            value,
            "to_dict",
        ):

            try:
                return value.to_dict()

            except Exception:
                pass


        if hasattr(
            value,
            "__dict__",
        ):

            return {
                key: item
                for key, item in vars(value).items()
                if not key.startswith("_")
            }


        return {}