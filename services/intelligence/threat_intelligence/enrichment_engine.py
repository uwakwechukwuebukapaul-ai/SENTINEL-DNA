"""
Sentinel DNA Threat Intelligence Enrichment Engine.
"""

from importlib import import_module


try:
    IOCExtractor = import_module(
        ".ioc_extractor",
        package=__package__,
    ).IOCExtractor
except ModuleNotFoundError as exc:
    if exc.name != f"{__package__}.ioc_extractor":
        raise

    class IOCExtractor:
        """Fallback extractor used when the optional IOC module is absent."""

        def extract(self, data):
            return []



class EnrichmentEngine:
    """
    IOC enrichment, reputation and ATT&CK mapping.
    """


    def __init__(
        self,
        extractor=None,
    ):

        self.extractor = (
            extractor
            or IOCExtractor()
        )


    def enrich(
        self,
        data,
    ):

        indicators = (
            self.extractor.extract(
                data
            )
        )


        enriched = []

        total_risk = 0


        for indicator in indicators:

            value = (
                indicator["value"]
                .lower()
            )


            malicious = any(
                keyword in value
                for keyword in [
                    "malicious",
                    "evil",
                    "phish",
                    ".xyz",
                    ".top",
                    ".click",
                ]
            )


            if malicious:

                risk_score = 90
                risk = "critical"
                reputation = "malicious"

            else:

                risk_score = 10
                risk = "low"
                reputation = "unknown"



            enriched_indicator = {

                **indicator,


                "reputation":
                    reputation,


                "risk":
                    risk,


                "risk_score":
                    risk_score,


                "attack_patterns":
                    [
                        "T1566"
                    ]
                    if malicious
                    else [],

            }


            total_risk += risk_score


            enriched.append(
                enriched_indicator
            )


        return {

            "indicators":
                enriched,


            "risk_score":
                total_risk,

        }