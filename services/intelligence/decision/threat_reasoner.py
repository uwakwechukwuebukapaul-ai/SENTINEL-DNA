"""
Sentinel DNA Threat Reasoner
"""


class ThreatReasoner:


    def analyze(
        self,
        alert: dict,
    ) -> list[str]:


        recommendations = []


        if alert.get(
            "ioc_count",
            0,
        ):

            recommendations.append(
                "perform_ioc_enrichment"
            )


        if alert.get(
            "user_impact",
            False,
        ):

            recommendations.append(
                "investigate_identity_activity"
            )


        if not recommendations:

            recommendations.append(
                "collect_additional_evidence"
            )


        return recommendations