"""
Evidence Correlation Engine.

Transforms raw investigation artifacts
into correlated security signals.
"""


from typing import Any


class EvidenceCorrelator:

    def correlate(
        self,
        artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]:

        indicators = []

        for artifact in artifacts:

            if not isinstance(
                artifact,
                dict,
            ):
                continue


            for key, value in artifact.items():

                if isinstance(
                    value,
                    str,
                ):

                    indicators.append(
                        {
                            "source": key,
                            "value": value,
                        }
                    )


        return {

            "indicator_count":
                len(indicators),

            "indicators":
                indicators,

        }