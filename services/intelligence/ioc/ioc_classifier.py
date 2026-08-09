"""
IOC Classification Engine
"""

import re


class IOCClassifier:
    """
    Detect IOC category.
    """

    def classify(
        self,
        indicator: str,
    ) -> str:

        value = indicator.lower().strip()


        if re.match(
            r"^\d{1,3}(\.\d{1,3}){3}$",
            value,
        ):
            return "ip"


        if value.startswith(
            (
                "http://",
                "https://",
            )
        ):
            return "url"


        if re.match(
            r"^[a-f0-9]{32}$",
            value,
        ):
            return "md5"


        if re.match(
            r"^[a-f0-9]{40}$",
            value,
        ):
            return "sha1"


        if re.match(
            r"^[a-f0-9]{64}$",
            value,
        ):
            return "sha256"


        return "domain"