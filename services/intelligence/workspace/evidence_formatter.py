"""
Sentinel DNA Evidence Formatter

Normalizes investigation evidence into
analyst workspace compatible structures.

Supports:

- IOC evidence
- Artifact evidence
- Correlation evidence
- Threat intelligence evidence
- Enrichment results
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class EvidenceFormatter:
    """
    Enterprise evidence normalization service.
    """


    def format(
        self,
        evidence: Any,
    ) -> dict[str, Any]:
        """
        Convert evidence into analyst-ready format.
        """

        normalized = self._normalize(
            evidence
        )

        return {

            "id":
                normalized.get(
                    "id"
                ),

            "type":
                normalized.get(
                    "type",
                    normalized.get(
                        "entity_type",
                        "unknown",
                    ),
                ),

            "value":
                normalized.get(
                    "value",
                    normalized.get(
                        "ioc",
                        normalized.get(
                            "indicator",
                        ),
                    ),
                ),

            "source":
                normalized.get(
                    "source",
                    "unknown",
                ),

            "confidence":
                self._confidence(
                    normalized
                ),

            "risk":
                normalized.get(
                    "risk",
                    "unknown",
                ),

            "enrichment":
                normalized.get(
                    "enrichment",
                    {},
                ),

            "metadata":
                normalized.get(
                    "metadata",
                    {},
                ),

            "created_at":
                normalized.get(
                    "created_at",
                    self._timestamp(),
                ),
        }



    def format_many(
        self,
        evidence_items: list[Any],
    ) -> list[dict[str, Any]]:
        """
        Format multiple evidence items.
        """

        return [
            self.format(item)
            for item in evidence_items
        ]



    def merge(
        self,
        evidence: list[Any],
    ) -> dict[str, Any]:
        """
        Create evidence collection summary.
        """

        formatted = self.format_many(
            evidence
        )


        return {

            "count":
                len(formatted),

            "items":
                formatted,

            "types":
                sorted(
                    {
                        item["type"]
                        for item in formatted
                    }
                ),

            "high_confidence":
                [
                    item
                    for item in formatted
                    if item["confidence"] >= 0.8
                ],

            "generated_at":
                self._timestamp(),
        }



    @staticmethod
    def _normalize(
        value: Any,
    ) -> dict[str, Any]:
        """
        Normalize objects and dictionaries.
        """

        if value is None:
            return {}


        if isinstance(
            value,
            dict,
        ):
            return dict(value)


        if hasattr(
            value,
            "to_dict",
        ):
            try:
                return value.to_dict()
            except Exception:
                pass


        from services.core.serialization import serialize
        normalized = serialize(value)
        return normalized if isinstance(normalized, dict) else {"value": normalized}



    @staticmethod
    def _confidence(
        evidence: dict[str, Any],
    ) -> float:
        """
        Extract confidence safely.
        """

        value = evidence.get(
            "confidence",
            0.0,
        )

        try:
            return float(value)

        except (
            TypeError,
            ValueError,
        ):
            return 0.0



    @staticmethod
    def _timestamp() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()
