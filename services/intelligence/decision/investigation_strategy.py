"""
Sentinel DNA Investigation Strategy Selector
"""


class InvestigationStrategy:


    def select(
        self,
        alert: dict,
    ) -> str:


        alert_type = (
            alert.get(
                "type",
                "unknown",
            )
            .lower()
        )


        strategies = {

            "phishing":
                "phishing_investigation",

            "malware":
                "malware_investigation",

            "login":
                "identity_investigation",

        }


        return strategies.get(
            alert_type,
            "general_investigation",
        )