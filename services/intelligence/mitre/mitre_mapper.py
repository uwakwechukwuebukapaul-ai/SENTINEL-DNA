"""
Sentinel DNA MITRE ATT&CK Mapper

Maps investigation reports and artifacts
to adversary techniques.
"""

from __future__ import annotations

from typing import Any

from .technique_database import (
    MITRE_TECHNIQUES,
)

from .tactic_classifier import (
    TacticClassifier,
)



class MitreMapper:
    """
    Enterprise ATT&CK mapping engine.
    """


    def __init__(self):

        self.classifier = (
            TacticClassifier()
        )



    def map(
        self,
        investigation_report: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Map AI investigation report.
        """

        threat = (
            investigation_report
            .get(
                "threat_assessment",
                "",
            )
        )


        technique = (
            MITRE_TECHNIQUES
            .get(
                threat
            )
        )


        if not technique:

            return {

                "technique_id":
                    None,

                "technique_name":
                    None,

                "tactic":
                    "Unknown",

                "confidence":
                    0,
            }



        return {

            "technique_id":
                technique[
                    "technique_id"
                ],


            "technique_name":
                technique[
                    "technique_name"
                ],


            "tactic":
                self.classifier.classify(
                    technique
                ),


            "description":
                technique[
                    "description"
                ],


            "confidence":
                90,
        }



    def map_artifact(
        self,
        artifact: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Map raw evidence artifacts
        to MITRE ATT&CK techniques.

        Supported:
        - email
        - file
        - credential
        """

        artifact_type = (
            artifact
            .get(
                "type",
                "",
            )
            .lower()
        )


        mappings = []


        if artifact_type == "email":

            mappings.append(

                {

                    "technique_id":
                        "T1566.002",


                    "technique_name":
                        "Phishing: Spearphishing Link",


                    "tactic":
                        "Initial Access",


                    "confidence":
                        90,

                }

            )



        elif artifact_type == "file":

            mappings.append(

                {

                    "technique_id":
                        "T1204.002",


                    "technique_name":
                        "Malicious File",


                    "tactic":
                        "Execution",


                    "confidence":
                        80,

                }

            )



        elif artifact_type == "credential":

            mappings.append(

                {

                    "technique_id":
                        "T1555",


                    "technique_name":
                        "Credentials from Password Stores",


                    "tactic":
                        "Credential Access",


                    "confidence":
                        85,

                }

            )



        return mappings