"""
Sentinel DNA Entity Resolver

Normalizes investigation entities.
"""

from __future__ import annotations

from typing import Any


class EntityResolver:


    def resolve(
        self,
        alert: dict[str, Any],
    ) -> list[dict[str, Any]]:

        entities = []


        for key in (
            "user",
            "username",
            "host",
            "hostname",
            "ip",
            "source_ip",
        ):

            if key in alert:

                entities.append(
                    {
                        "type": key,
                        "value": alert[key],
                    }
                )


        return entities