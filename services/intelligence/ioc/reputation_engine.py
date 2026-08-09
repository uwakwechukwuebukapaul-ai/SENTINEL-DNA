"""
IOC Reputation Analysis Engine

Future integrations:
- VirusTotal
- AbuseIPDB
- AlienVault OTX
- MISP
- ThreatFox
"""


class ReputationEngine:


    def analyze(
        self,
        indicator: str,
        indicator_type: str,
    ) -> dict:


        value = indicator.lower()


        suspicious_patterns = [
            ".xyz",
            ".top",
            ".click",
            ".zip",
            ".ru",
            "phish",
            "malware",
            "payload",
            "login",
        ]


        risk = "low"
        confidence = 0.25


        for pattern in suspicious_patterns:

            if pattern in value:

                risk = "high"

                confidence = 0.90

                break


        return {

            "risk": risk,

            "confidence": confidence,

            "indicator_type": indicator_type,

            "engine":
                "sentinel-dna-reputation-engine",

        }