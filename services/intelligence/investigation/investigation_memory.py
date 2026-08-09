"""
Sentinel DNA Investigation Memory

Stores previous investigations
for future intelligence reuse.
"""

from __future__ import annotations

from typing import Any


class InvestigationMemory:


    def __init__(self):

        self.memory: list[
            dict[str, Any]
        ] = []


    def store(
        self,
        investigation: dict[str, Any],
    ) -> None:

        self.memory.append(
            investigation
        )


    def search(
        self,
        value: str,
    ) -> list[dict[str, Any]]:

        matches = []


        for item in self.memory:

            if value in str(item):

                matches.append(
                    item
                )


        return matches


    def all(
        self,
    ) -> list[dict[str, Any]]:

        return self.memory