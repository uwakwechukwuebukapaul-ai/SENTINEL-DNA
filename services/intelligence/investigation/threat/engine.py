"""
Sentinel DNA Threat Intelligence Correlation Engine.

Responsibilities:

- Correlate IOC intelligence with threat patterns
- Identify likely campaign context
- Identify known/suspected actor context
- Map attack patterns to MITRE ATT&CK
- Calculate severity and confidence
- Build investigation-ready threat context

This implementation intentionally uses deterministic local
correlation rules. External providers can be integrated later
without changing the public engine contract.
"""

from typing import Any

from .models import (
    ThreatContext,
    ThreatIntelligenceCollection,
)


class ThreatIntelligenceEngine:
    """
    Correlates IOC intelligence into structured threat context.
    """

    ENGINE_NAME = "threat_intelligence_correlation"

    DEFAULT_SOURCE = "sentinel_dna_threat_engine"

    def correlate(
        self,
        case_id: str,
        indicators: list[Any] | None = None,
    ) -> ThreatIntelligenceCollection:
        """
        Correlate a collection of indicators.

        Each indicator may be:

        - a string
        - a dictionary
        - an IOCRecord
        - another object exposing to_dict()
        """

        normalized = self._normalize_indicators(
            indicators
        )

        threats: list[ThreatContext] = []

        for indicator in normalized:
            threats.append(
                self._correlate_indicator(
                    indicator
                )
            )

        return ThreatIntelligenceCollection(
            case_id=case_id,
            threats=threats,
            metadata={
                "engine": self.ENGINE_NAME,
                "indicator_count": len(normalized),
                "threat_count": len(threats),
            },
        )

    def analyze_campaign(
        self,
        indicator: Any,
    ) -> str:
        """
        Determine likely campaign context.

        This is a deterministic baseline intended to be
        replaced or supplemented by external intelligence.
        """

        data = self._normalize_indicator(
            indicator
        )

        value = self._indicator_value(
            data
        ).lower()

        context = self._combined_context(
            data
        )

        phishing_terms = (
            "login",
            "verify",
            "credential",
            "password",
            "account",
            "signin",
            "authentication",
        )

        malware_terms = (
            "malware",
            "payload",
            "trojan",
            "ransomware",
            "backdoor",
        )

        if any(
            term in context
            for term in phishing_terms
        ):

            return "Credential Phishing Campaign"

        if any(
            term in context
            for term in malware_terms
        ):

            return "Malware Delivery Campaign"

        if self._looks_like_suspicious_domain(
            value
        ):

            return "Suspicious Infrastructure Campaign"

        return "Unknown"

    def identify_actor(
        self,
        indicator: Any,
    ) -> str:
        """
        Identify a likely threat actor when local
        deterministic intelligence supports one.

        Unknown is returned when attribution cannot be
        established. Sentinel DNA must not fabricate attribution.
        """

        data = self._normalize_indicator(
            indicator
        )

        context = self._combined_context(
            data
        )

        actor = data.get(
            "actor"
        )

        if actor:
            return str(
                actor
            )

        explicit_actor = data.get(
            "threat_actor"
        )

        if explicit_actor:
            return str(
                explicit_actor
            )

        known_actor = self._lookup_actor(
            context
        )

        if known_actor:
            return known_actor

        return "Unknown"

    def map_attack_patterns(
        self,
        indicator: Any,
    ) -> list[str]:
        """
        Map observed intelligence to MITRE ATT&CK
        techniques.
        """

        data = self._normalize_indicator(
            indicator
        )

        existing = self._extract_string_list(
            data.get(
                "mitre_techniques"
            )
        )

        existing.extend(
            self._extract_string_list(
                data.get(
                    "attack_patterns"
                )
            )
        )

        indicator_type = str(
            data.get(
                "indicator_type",
                data.get(
                    "type",
                    "unknown",
                ),
            )
        ).lower()

        context = self._combined_context(
            data
        )

        techniques: list[str] = []

        for technique in existing:
            if technique not in techniques:
                techniques.append(
                    technique
                )

        if (
            indicator_type in {
                "url",
                "domain",
            }
            and "T1566.002" not in techniques
        ):
            techniques.append(
                "T1566.002"
            )

        if (
            indicator_type == "ip_address"
            and "T1071" not in techniques
        ):
            techniques.append(
                "T1071"
            )

        if (
            indicator_type == "hash"
            and "T1204" not in techniques
        ):
            techniques.append(
                "T1204"
            )

        if any(
            term in context
            for term in (
                "credential",
                "password",
                "login",
                "signin",
                "authentication",
            )
        ):

            if "T1056.002" not in techniques:
                techniques.append(
                    "T1056.002"
                )

        if any(
            term in context
            for term in (
                "phishing",
                "spearphishing",
                "attachment",
            )
        ):

            if "T1566" not in techniques:
                techniques.append(
                    "T1566"
                )

        return techniques

    def calculate_severity(
        self,
        indicator: Any,
    ) -> str:
        """
        Calculate deterministic threat severity.
        """

        data = self._normalize_indicator(
            indicator
        )

        explicit = data.get(
            "severity"
        )

        if explicit:
            normalized = str(
                explicit
            ).lower().strip()

            if normalized in {
                "critical",
                "high",
                "medium",
                "low",
                "unknown",
            }:
                return normalized

        reputation = str(
            data.get(
                "reputation",
                "unknown",
            )
        ).lower()

        risk = str(
            data.get(
                "risk",
                "low",
            )
        ).lower()

        context = self._combined_context(
            data
        )

        if reputation == "malicious":
            return "critical"

        if risk in {
            "critical",
            "high",
        }:
            return risk

        if any(
            term in context
            for term in (
                "credential",
                "phishing",
                "malware",
                "ransomware",
                "payload",
            )
        ):
            return "high"

        if self._looks_like_suspicious_domain(
            context
        ):
            return "high"

        if risk == "medium":
            return "medium"

        return "low"

    def calculate_confidence(
        self,
        indicator: Any,
        techniques: list[str] | None = None,
    ) -> int:
        """
        Calculate bounded intelligence confidence.
        """

        data = self._normalize_indicator(
            indicator
        )

        explicit = data.get(
            "confidence"
        )

        if explicit is not None:
            try:
                value = int(
                    explicit
                )

                return max(
                    0,
                    min(
                        100,
                        value,
                    ),
                )

            except (
                TypeError,
                ValueError,
            ):
                pass

        score = 40

        reputation = str(
            data.get(
                "reputation",
                "unknown",
            )
        ).lower()

        indicator_type = str(
            data.get(
                "indicator_type",
                data.get(
                    "type",
                    "unknown",
                ),
            )
        ).lower()

        if reputation == "malicious":
            score += 35
        elif reputation in {
            "suspicious",
            "bad",
        }:
            score += 20

        if indicator_type != "unknown":
            score += 15

        if techniques:
            score += min(
                10,
                len(techniques) * 5,
            )

        return max(
            0,
            min(
                100,
                score,
            ),
        )

    def build_context(
        self,
        collection: ThreatIntelligenceCollection,
    ) -> dict[str, Any]:
        """
        Build investigation-ready threat context.
        """

        threats = collection.threats

        mitre: list[str] = []
        related: list[str] = []
        high_risk: list[str] = []

        for threat in threats:

            for technique in (
                threat.mitre_techniques
            ):

                if technique not in mitre:
                    mitre.append(
                        technique
                    )

            for indicator in (
                threat.related_indicators
            ):

                if indicator not in related:
                    related.append(
                        indicator
                    )

            if threat.severity in {
                "critical",
                "high",
            }:

                high_risk.append(
                    threat.indicator
                )

        return {
            "case_id": collection.case_id,
            "threat_count": len(threats),
            "high_risk_indicators": high_risk,
            "mitre_techniques": mitre,
            "related_indicators": related,
            "threats": [
                threat.to_dict()
                for threat in threats
            ],
            "metadata": {
                **collection.metadata,
                "context_engine": self.ENGINE_NAME,
            },
        }

    def _correlate_indicator(
        self,
        indicator: Any,
    ) -> ThreatContext:
        """
        Build a ThreatContext for one indicator.
        """

        data = self._normalize_indicator(
            indicator
        )

        value = self._indicator_value(
            data
        )

        techniques = (
            self.map_attack_patterns(
                data
            )
        )

        campaign = (
            self.analyze_campaign(
                data
            )
        )

        actor = (
            self.identify_actor(
                data
            )
        )

        severity = (
            self.calculate_severity(
                data
            )
        )

        confidence = (
            self.calculate_confidence(
                data,
                techniques,
            )
        )

        threat_name = (
            self._build_threat_name(
                campaign,
                severity,
            )
        )

        related = (
            self._extract_related_indicators(
                data
            )
        )

        attack_patterns = (
            self._build_attack_patterns(
                data,
                techniques,
            )
        )

        return ThreatContext(

            indicator=value,

            threat_name=threat_name,

            actor=actor,

            campaign=campaign,

            severity=severity,

            confidence=confidence,

            mitre_techniques=techniques,

            attack_patterns=attack_patterns,

            related_indicators=related,

            sources=self._sources(
                data
            ),

            metadata={
                "engine": self.ENGINE_NAME,
                "provider": "local_deterministic",
                "attribution_confidence": (
                    0
                    if actor == "Unknown"
                    else confidence
                ),
            },
        )

    def _normalize_indicators(
        self,
        indicators: list[Any] | None,
    ) -> list[Any]:

        if indicators is None:
            return []

        if isinstance(
            indicators,
            (list, tuple, set),
        ):
            return list(
                indicators
            )

        return [
            indicators
        ]

    def _normalize_indicator(
        self,
        indicator: Any,
    ) -> dict[str, Any]:
        """
        Normalize supported IOC representations.
        """

        if isinstance(
            indicator,
            dict,
        ):
            return dict(
                indicator
            )

        to_dict = getattr(
            indicator,
            "to_dict",
            None,
        )

        if callable(
            to_dict
        ):
            result = to_dict()

            if isinstance(
                result,
                dict,
            ):
                return dict(
                    result
                )

        value = getattr(
            indicator,
            "indicator",
            None,
        )

        if value is not None:
            return {
                "indicator": value,
                "indicator_type": getattr(
                    indicator,
                    "indicator_type",
                    "unknown",
                ),
                "risk": getattr(
                    indicator,
                    "risk",
                    "low",
                ),
                "confidence": getattr(
                    indicator,
                    "confidence",
                    50,
                ),
                "reputation": getattr(
                    indicator,
                    "reputation",
                    "unknown",
                ),
                "mitre_techniques": getattr(
                    indicator,
                    "mitre_techniques",
                    [],
                ),
                "sources": getattr(
                    indicator,
                    "sources",
                    [],
                ),
                "context": getattr(
                    indicator,
                    "context",
                    {},
                ),
            }

        return {
            "indicator": str(
                indicator
            )
        }

    def _indicator_value(
        self,
        data: dict[str, Any],
    ) -> str:

        value = data.get(
            "indicator"
        )

        if value is None:
            value = data.get(
                "value",
                "",
            )

        return str(
            value
        ).strip()

    def _combined_context(
        self,
        data: dict[str, Any],
    ) -> str:

        parts = [
            self._indicator_value(
                data
            ),
            str(
                data.get(
                    "context",
                    "",
                )
            ),
            str(
                data.get(
                    "threat_name",
                    "",
                )
            ),
            str(
                data.get(
                    "campaign",
                    "",
                )
            ),
        ]

        return " ".join(
            parts
        ).lower()

    def _looks_like_suspicious_domain(
        self,
        value: str,
    ) -> bool:

        suspicious = (
            ".xyz",
            ".top",
            ".click",
            ".ru",
            ".tk",
            ".zip",
            "evil",
            "malware",
        )

        normalized = value.lower()

        return any(
            pattern in normalized
            for pattern in suspicious
        )

    def _lookup_actor(
        self,
        context: str,
    ) -> str | None:
        """
        Conservative actor attribution.

        Attribution is only returned when an explicit
        deterministic mapping exists.
        """

        mappings = {
            "apt28": "APT28",
            "fancy bear": "APT28",
            "apt29": "APT29",
            "cozy bear": "APT29",
            "lazarus": "Lazarus Group",
            "lazarus group": "Lazarus Group",
        }

        for pattern, actor in mappings.items():

            if pattern in context:
                return actor

        return None

    def _extract_string_list(
        self,
        value: Any,
    ) -> list[str]:

        if value is None:
            return []

        if isinstance(
            value,
            str,
        ):
            return [
                value
            ]

        if isinstance(
            value,
            (list, tuple, set),
        ):
            return [
                str(item)
                for item in value
                if str(item).strip()
            ]

        return [
            str(value)
        ]

    def _extract_related_indicators(
        self,
        data: dict[str, Any],
    ) -> list[str]:

        related = (
            data.get(
                "related_indicators"
            )
        )

        return self._extract_string_list(
            related
        )

    def _sources(
        self,
        data: dict[str, Any],
    ) -> list[str]:

        sources = (
            self._extract_string_list(
                data.get(
                    "sources"
                )
            )
        )

        if not sources:
            sources = [
                self.DEFAULT_SOURCE
            ]

        return list(
            dict.fromkeys(
                sources
            )
        )

    def _build_threat_name(
        self,
        campaign: str,
        severity: str,
    ) -> str:

        if campaign != "Unknown":
            return campaign

        if severity == "critical":
            return "Critical Threat Indicator"

        if severity == "high":
            return "High-Risk Threat Indicator"

        if severity == "medium":
            return "Suspicious Threat Indicator"

        return "Unknown Threat"

    def _build_attack_patterns(
        self,
        data: dict[str, Any],
        techniques: list[str],
    ) -> list[str]:

        patterns = (
            self._extract_string_list(
                data.get(
                    "attack_patterns"
                )
            )
        )

        context = self._combined_context(
            data
        )

        if (
            any(
                term in context
                for term in (
                    "credential",
                    "login",
                    "password",
                    "signin",
                )
            )
            and "Credential Access" not in patterns
        ):
            patterns.append(
                "Credential Access"
            )

        if (
            any(
                term in context
                for term in (
                    "phishing",
                    "spearphishing",
                )
            )
            and "Phishing" not in patterns
        ):
            patterns.append(
                "Phishing"
            )

        if (
            techniques
            and "Threat Intelligence Correlation"
            not in patterns
        ):
            patterns.append(
                "Threat Intelligence Correlation"
            )

        return list(
            dict.fromkeys(
                patterns
            )
        )