"""
Sentinel DNA Threat Normalizer

Normalizes raw SOC artifacts into
structured intelligence objects.
"""

from __future__ import annotations

import re
from typing import Any


class ThreatNormalizer:
    """
    Converts raw alert data into
    investigation-ready format.
    """


    def normalize(
        self,
        alert: dict[str, Any],
    ) -> dict[str, Any]:

        return {
            "text": self._clean_text(alert),
            "artifacts": self._extract_artifacts(alert),
            "category": alert.get(
                "category",
                "unknown",
            ),
            "severity": alert.get(
                "severity",
                "unknown",
            ),
        }


    def _clean_text(
        self,
        alert: dict[str, Any],
    ) -> str:

        text = str(alert)

        # Remove markdown links
        text = re.sub(
            r"\[([^\]]+)\]\([^)]+\)",
            r"\1",
            text,
        )

        return text


    def _extract_artifacts(
        self,
        alert: dict[str, Any],
    ) -> list[dict[str, Any]]:

        artifacts = []

        for item in alert.get(
            "artifacts",
            [],
        ):

            if isinstance(
                item,
                dict,
            ):
                artifacts.append(
                    {
                        "type": item.get(
                            "type",
                            "unknown",
                        ),
                        "value": self._clean_value(
                            item.get(
                                "value",
                                item.get(
                                    "sender",
                                    "",
                                ),
                            )
                        ),
                    }
                )

        return artifacts


    def _clean_value(
        self,
        value: str,
    ) -> str:

        value = str(value)

        match = re.search(
            r"(https?://[^\s\]]+)",
            value,
        )

        if match:
            return match.group(1)

        return value.strip(
            "[]{}',\""
        )