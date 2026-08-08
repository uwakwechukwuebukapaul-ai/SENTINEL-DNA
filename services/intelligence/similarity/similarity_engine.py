"""
Sentinel DNA Investigation Similarity Engine

Compares investigations against historical cases.
"""

from __future__ import annotations

from typing import Any


class SimilarityEngine:
    """
    Investigation comparison engine.

    Current:
        Rule-based similarity.

    Future:
        Vector embeddings.
        LLM reasoning.
        Graph similarity.
    """

    def __init__(self) -> None:

        self.history: list[
            dict[str, Any]
        ] = []


    def register_investigation(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Store investigation for comparison.
        """

        self.history.append(
            investigation
        )

        return investigation


    def compare(
        self,
        investigation: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Compare investigation against history.
        """

        results = []

        for item in self.history:

            score = self._calculate_similarity(
                investigation,
                item,
            )

            results.append(
                {
                    "investigation": item,
                    "similarity_score": score,
                }
            )

        return sorted(
            results,
            key=lambda x: x["similarity_score"],
            reverse=True,
        )


    def _calculate_similarity(
        self,
        first: dict[str, Any],
        second: dict[str, Any],
    ) -> float:
        """
        Calculate similarity score.
        """

        score = 0


        first_iocs = set(
            first.get(
                "iocs",
                [],
            )
        )

        second_iocs = set(
            second.get(
                "iocs",
                [],
            )
        )


        if first_iocs and second_iocs:

            overlap = (
                len(
                    first_iocs.intersection(
                        second_iocs
                    )
                )
                /
                len(
                    first_iocs.union(
                        second_iocs
                    )
                )
            )

            score += overlap * 50


        first_techniques = set(
            first.get(
                "techniques",
                [],
            )
        )

        second_techniques = set(
            second.get(
                "techniques",
                [],
            )
        )


        if first_techniques and second_techniques:

            overlap = (
                len(
                    first_techniques.intersection(
                        second_techniques
                    )
                )
                /
                len(
                    first_techniques.union(
                        second_techniques
                    )
                )
            )

            score += overlap * 50


        return round(
            score,
            2,
        )


    def clear_history(self) -> None:
        """
        Clear stored investigations.
        """

        self.history.clear()