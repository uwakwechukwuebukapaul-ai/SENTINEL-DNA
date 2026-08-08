"""
Sentinel DNA Evidence Store

Stores normalized investigation evidence.
"""

from __future__ import annotations

from .evidence_model import Evidence


class EvidenceStore:


    def __init__(self):

        self._evidence = []



    def add(
        self,
        evidence: Evidence,
    ):

        self._evidence.append(
            evidence
        )



    def all(self):

        return self._evidence



    def count(self):

        return len(
            self._evidence
        )



    def to_list(self):

        return [
            item.to_dict()
            for item in self._evidence
        ]