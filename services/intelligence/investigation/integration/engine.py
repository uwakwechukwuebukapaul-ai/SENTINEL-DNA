"""
Sentinel DNA Investigation Intelligence Integration Engine.

Combines outputs from the individual investigation intelligence
layers into one normalized investigation intelligence object.

This layer performs orchestration and normalization only.

It does not reimplement:

- Evidence analysis
- IOC enrichment
- Threat intelligence
- Graph construction
- Timeline generation
- AI reasoning
- Decision intelligence
"""

from __future__ import annotations

from typing import Any

from .models import InvestigationIntegrationResult


class InvestigationIntelligenceIntegrationEngine:
    """
    Integrates investigation intelligence outputs.

    Supported domains:

    - Evidence
    - IOC intelligence
    - Threat intelligence
    - Investigation graph
    - Investigation timeline
    """

    def integrate(
        self,
        case_id: str,
        evidence: Any = None,
        iocs: Any = None,
        threats: Any = None,
        graph: Any = None,
        timeline: Any = None,
    ) -> InvestigationIntegrationResult:
        """
        Integrate all available investigation intelligence.
        """

        normalized_evidence = self._extract_collection(
            evidence,
            "evidence",
        )

        normalized_iocs = self._extract_collection(
            iocs,
            "iocs",
        )

        normalized_threats = self._extract_collection(
            threats,
            "threats",
        )

        risk = self._derive_risk(
            evidence=normalized_evidence,
            iocs=normalized_iocs,
            threats=normalized_threats,
            graph=graph,
            timeline=timeline,
        )

        confidence = self._derive_confidence(
            evidence=normalized_evidence,
            iocs=normalized_iocs,
            threats=normalized_threats,
            graph=graph,
            timeline=timeline,
        )

        metadata = {
            "engine": (
                "investigation_intelligence_integration"
            ),
            "evidence_count": len(
                normalized_evidence
            ),
            "ioc_count": len(
                normalized_iocs
            ),
            "threat_count": len(
                normalized_threats
            ),
            "graph_present": graph is not None,
            "timeline_present": timeline is not None,
            "risk": risk,
            "confidence": confidence,
        }

        return InvestigationIntegrationResult(
            case_id=case_id,
            evidence=normalized_evidence,
            iocs=normalized_iocs,
            threats=normalized_threats,
            graph=graph,
            timeline=timeline,
            risk=risk,
            confidence=confidence,
            metadata=metadata,
        )

    def execute(
        self,
        case_id: str,
        evidence: Any = None,
        iocs: Any = None,
        threats: Any = None,
        graph: Any = None,
        timeline: Any = None,
    ) -> InvestigationIntegrationResult:
        """
        Compatibility execution alias.
        """

        return self.integrate(
            case_id=case_id,
            evidence=evidence,
            iocs=iocs,
            threats=threats,
            graph=graph,
            timeline=timeline,
        )

    def _extract_collection(
        self,
        value: Any,
        preferred_key: str,
    ) -> list[Any]:
        """
        Normalize engine results into a list.
        """

        if value is None:
            return []

        normalized = self._serialize(
            value
        )

        if isinstance(
            normalized,
            dict,
        ):
            candidate = normalized.get(
                preferred_key
            )

            if candidate is None:
                candidate = normalized.get(
                    self._singular_key(
                        preferred_key
                    )
                )

            if candidate is not None:
                normalized = candidate
            else:
                return [normalized]

        if isinstance(
            normalized,
            list,
        ):
            return list(
                normalized
            )

        if isinstance(
            normalized,
            tuple,
        ):
            return list(
                normalized
            )

        return [normalized]

    @staticmethod
    def _singular_key(
        key: str,
    ) -> str:
        """
        Return the common singular form of collection names.
        """

        mapping = {
            "evidence": "finding",
            "iocs": "ioc",
            "threats": "threat",
        }

        return mapping.get(
            key,
            key,
        )

    def _derive_risk(
        self,
        evidence: list[Any],
        iocs: list[Any],
        threats: list[Any],
        graph: Any,
        timeline: Any,
    ) -> str:
        """
        Select the highest explicit risk observed.
        """

        risks: list[str] = []

        risks.extend(
            self._collect_risks(
                evidence
            )
        )

        risks.extend(
            self._collect_risks(
                iocs
            )
        )

        risks.extend(
            self._collect_risks(
                threats
            )
        )

        risks.extend(
            self._collect_object_risks(
                graph
            )
        )

        risks.extend(
            self._collect_object_risks(
                timeline
            )
        )

        if not risks:
            return "low"

        priority = {
            "unknown": 0,
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4,
        }

        return max(
            risks,
            key=lambda value: priority.get(
                value,
                0,
            ),
        )

    def _collect_risks(
        self,
        items: list[Any],
    ) -> list[str]:
        """
        Extract risk/severity values from collections.
        """

        risks: list[str] = []

        for item in items:

            if not isinstance(
                item,
                dict,
            ):
                continue

            for key in (
                "risk",
                "severity",
            ):

                normalized = self._normalize_risk(
                    item.get(key)
                )

                if normalized:
                    risks.append(
                        normalized
                    )

        return risks

    def _collect_object_risks(
        self,
        value: Any,
    ) -> list[str]:
        """
        Extract risk/severity values from model objects.
        """

        if value is None:
            return []

        normalized = self._serialize(
            value
        )

        if not isinstance(
            normalized,
            dict,
        ):
            return []

        risks: list[str] = []

        for key in (
            "risk",
            "severity",
        ):

            risk = self._normalize_risk(
                normalized.get(key)
            )

            if risk:
                risks.append(
                    risk
                )

        return risks

    def _derive_confidence(
        self,
        evidence: list[Any],
        iocs: list[Any],
        threats: list[Any],
        graph: Any,
        timeline: Any,
    ) -> int:
        """
        Derive deterministic aggregate confidence.
        """

        values: list[int] = []

        for collection in (
            evidence,
            iocs,
            threats,
        ):

            for item in collection:

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                confidence = (
                    self._normalize_confidence(
                        item.get(
                            "confidence"
                        )
                    )
                )

                if confidence is not None:
                    values.append(
                        confidence
                    )

        for value in (
            graph,
            timeline,
        ):

            normalized = self._serialize(
                value
            )

            if not isinstance(
                normalized,
                dict,
            ):
                continue

            confidence = (
                self._normalize_confidence(
                    normalized.get(
                        "confidence"
                    )
                )
            )

            if confidence is not None:
                values.append(
                    confidence
                )

        if not values:
            return 50

        return int(
            round(
                sum(values)
                / len(values)
            )
        )

    @staticmethod
    def _normalize_risk(
        value: Any,
    ) -> str | None:
        """
        Normalize risk labels.
        """

        if value is None:
            return None

        normalized = str(
            value
        ).strip().lower()

        aliases = {
            "informational": "low",
            "info": "low",
            "moderate": "medium",
            "severe": "high",
        }

        normalized = aliases.get(
            normalized,
            normalized,
        )

        if normalized in {
            "unknown",
            "low",
            "medium",
            "high",
            "critical",
        }:
            return normalized

        return None

    @staticmethod
    def _normalize_confidence(
        value: Any,
    ) -> int | None:
        """
        Normalize confidence to 0-100.
        """

        if value is None:
            return None

        try:
            confidence = int(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

        return max(
            0,
            min(
                100,
                confidence,
            ),
        )

    @classmethod
    def _serialize(
        cls,
        value: Any,
    ) -> Any:
        """
        Convert supported model objects to dictionaries.
        """

        if value is None:
            return None

        if isinstance(
            value,
            list,
        ):
            return [
                cls._serialize(item)
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                cls._serialize(item)
                for item in value
            ]

        if isinstance(
            value,
            dict,
        ):
            return {
                key: cls._serialize(item)
                for key, item in value.items()
            }

        to_dict = getattr(
            value,
            "to_dict",
            None,
        )

        if callable(to_dict):
            return cls._serialize(
                to_dict()
            )

        return value