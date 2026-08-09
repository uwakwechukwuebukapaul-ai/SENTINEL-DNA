"""
Sentinel DNA - IOC Extractor

Extract indicators of compromise
from security events.
"""

from __future__ import annotations

from typing import Any



class IOCExtractor:
    """
    Extracts IOC artifacts from events.
    """



    def extract(
        self,
        event: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Extract indicators.
        """

        indicators = []


        fields = [

            ("domain", "domain"),

            ("ip", "ip"),

            ("hash", "hash"),

            ("file_hash", "hash"),

            ("url", "url"),

            ("indicator", "unknown"),

        ]


        for field, ioc_type in fields:

            value = event.get(field)


            if value:

                indicators.append(

                    {

                        "type":
                            ioc_type,

                        "value":
                            value,

                    }

                )


        return indicators