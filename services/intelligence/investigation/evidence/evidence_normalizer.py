"""
Sentinel DNA Evidence Normalizer

Converts agent output into
standard evidence objects.
"""

from __future__ import annotations

from .evidence_model import Evidence


class EvidenceNormalizer:


    @staticmethod
    def normalize(
        agent_name,
        finding,
    ) -> Evidence:


        return Evidence(

            evidence_type="agent_finding",

            source=agent_name,

            value=finding,

            confidence=(
                finding.get(
                    "confidence",
                    0.0,
                )
                if isinstance(
                    finding,
                    dict,
                )
                else 0.0
            ),

        )