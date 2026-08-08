"""
Sentinel DNA MITRE ATT&CK Intelligence Engine

Maps investigation evidence
to adversary techniques.

Uses weighted matching priority.
"""

from __future__ import annotations


from .attack_mapping import (
    MITRE_TECHNIQUES,
)

from .technique import (
    MitreTechnique,
)



class MitreEngine:


    PRIORITY = [

        "phishing",

        "credential",

        "malicious-domain",

    ]



    def analyze(
        self,
        evidence,
    ):

        techniques = []


        for item in evidence:


            value = str(

                item.value

                if hasattr(
                    item,
                    "value",
                )

                else item

            ).lower()



            matched = False


            #
            # High confidence ATT&CK matching
            #

            for keyword in self.PRIORITY:


                if keyword in value:


                    data = (
                        MITRE_TECHNIQUES[
                            keyword
                        ]
                    )


                    techniques.append(

                        MitreTechnique(

                            technique_id=data["id"],

                            name=data["name"],

                            tactic=data["tactic"],

                            description=(
                                f"Detected from "
                                f"{keyword}"
                            ),

                        )

                    )


                    matched = True


                    break



            #
            # Fallback matching
            #

            if not matched:


                for keyword, data in MITRE_TECHNIQUES.items():


                    if keyword in value:


                        techniques.append(

                            MitreTechnique(

                                technique_id=data["id"],

                                name=data["name"],

                                tactic=data["tactic"],

                                description=(
                                    f"Detected from "
                                    f"{keyword}"
                                ),

                            )

                        )


                        break



        return techniques