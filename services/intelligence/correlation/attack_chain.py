"""
Attack chain builder.

Transforms intelligence signals
into analyst-readable attack progression.
"""


class AttackChainBuilder:


    def build(
        self,
        indicators,
        techniques,
    ):

        story = []


        if indicators:

            story.append(
                "Initial indicator discovery completed"
            )


        if techniques:

            story.append(
                "MITRE ATT&CK techniques identified"
            )


        if any(
            "credential" in str(item).lower()
            for item in techniques
        ):

            story.append(
                "Credential access activity suspected"
            )


        if not story:

            story.append(
                "Insufficient evidence for attack chain"
            )


        return story