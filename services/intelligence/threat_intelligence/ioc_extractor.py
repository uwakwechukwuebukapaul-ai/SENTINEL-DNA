"""
Sentinel DNA IOC Extractor.

Extracts:
- URLs
- Domains
- IP addresses
- Hashes
"""

from __future__ import annotations

import re


class IOCExtractor:
    """
    Extract indicators of compromise from evidence.
    """


    URL_REGEX = re.compile(
        r"https?://[^\s]+",
        re.IGNORECASE,
    )


    DOMAIN_REGEX = re.compile(
        r"\b[a-zA-Z0-9.-]+\.(com|net|org|xyz|top|ru|io|click|example)\b",
        re.IGNORECASE,
    )


    IP_REGEX = re.compile(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    )


    HASH_REGEX = re.compile(
        r"\b[a-fA-F0-9]{32,64}\b"
    )


    def extract(
        self,
        data,
    ) -> list[dict]:


        text = self._normalize(
            data
        )


        indicators = []


        # URLs
        for url in self.URL_REGEX.findall(text):

            indicators.append(
                {
                    "type": "url",
                    "value": url.rstrip(".,)")
                }
            )


        # Domains
        for domain in self.DOMAIN_REGEX.findall(text):

            pass


        domains = self.DOMAIN_REGEX.finditer(
            text
        )


        for match in domains:

            domain = match.group(0)


            if not any(
                item["value"] == domain
                for item in indicators
            ):

                indicators.append(
                    {
                        "type": "domain",
                        "value": domain,
                    }
                )


        # IP addresses
        for ip in self.IP_REGEX.findall(text):

            indicators.append(
                {
                    "type": "ip",
                    "value": ip,
                }
            )


        # Hashes
        for hash_value in self.HASH_REGEX.findall(text):

            indicators.append(
                {
                    "type": "hash",
                    "value": hash_value,
                }
            )


        return indicators



    def _normalize(
        self,
        data,
    ) -> str:


        if isinstance(data, dict):

            return " ".join(
                str(value)
                for value in data.values()
            )


        if isinstance(data, list):

            return " ".join(
                str(item)
                for item in data
            )


        return str(data)