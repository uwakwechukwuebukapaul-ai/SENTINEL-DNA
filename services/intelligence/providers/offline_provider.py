"""
Offline intelligence provider.

Provides local intelligence enrichment
without external APIs.
"""


from typing import Any


class OfflineIntelligenceProvider:

    name = "offline"


    MALICIOUS_DOMAINS = {
        "evil.com",
        "malicious.com",
        "phishing.com",
    }


    MALWARE_MAP = {
        "malicious.com": "DarkLoader",
    }


    def lookup(
        self,
        indicator: str,
        indicator_type: str,
    ) -> dict[str, Any]:

        indicator = indicator.lower()


        malicious = (
            indicator
            in self.MALICIOUS_DOMAINS
        )


        return {

            "indicator": indicator,

            "type": indicator_type,

            "malicious": malicious,

            "reputation": (
                "malicious"
                if malicious
                else "unknown"
            ),

            "confidence": (
                95
                if malicious
                else 10
            ),

            "malware": (
                self.MALWARE_MAP.get(
                    indicator
                )
            ),

        }