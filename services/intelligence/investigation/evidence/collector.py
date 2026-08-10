"""
Sentinel DNA Evidence Collector

Collects normalized investigation evidence.
"""


from .evidence_model import Evidence
from .evidence_store import EvidenceStore


class EvidenceCollector:
    """
    Collects evidence generated during investigation.
    """


    def __init__(self):

        self.store = EvidenceStore()


    def collect(self, task):

        evidence_items = []


        task_name = task.name.lower()


        if "indicator" in task_name:

            evidence = Evidence(
                evidence_type="ioc",
                source="investigation_executor",
                value="unknown_indicator",
                confidence=0.5,
                metadata={
                    "task": task.name
                },
            )


        elif "evidence" in task_name:

            evidence = Evidence(
                evidence_type="artifact",
                source="investigation_executor",
                value="collected_artifact",
                confidence=0.6,
                metadata={
                    "task": task.name
                },
            )


        else:

            evidence = Evidence(
                evidence_type="investigation_event",
                source="investigation_executor",
                value=task.name,
                confidence=0.4,
                metadata={
                    "task": task.name
                },
            )


        self.store.add(evidence)

        evidence_items.append(evidence)


        return evidence_items