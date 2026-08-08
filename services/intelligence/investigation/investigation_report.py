"""
Sentinel DNA Investigation Report

Final analyst-facing investigation object.
"""

from __future__ import annotations


class InvestigationReport:


    def __init__(
        self,
        case_id,
    ):

        self.case_id = case_id

        self.evidence = []

        self.timeline = []

        self.assessment = {}



    def add_evidence(
        self,
        evidence,
    ):

        self.evidence.append(
            evidence
        )



    def add_timeline_event(
        self,
        event,
    ):

        self.timeline.append(
            event
        )



    def to_dict(self):

        return {

            "case_id":
                self.case_id,

            "evidence":
                [
                    e.to_dict()
                    for e in self.evidence
                ],

            "timeline":
                [
                    e.__dict__
                    for e in self.timeline
                ],

            "assessment":
                self.assessment,
        }