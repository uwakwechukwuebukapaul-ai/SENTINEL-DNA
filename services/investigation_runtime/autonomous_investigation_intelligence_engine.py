"""
Autonomous Investigation Intelligence Engine.

Canonical runtime implementation for Sentinel DNA autonomous
investigation workflows.

The engine provides:
- investigation lifecycle management
- evidence analysis
- threat activity correlation
- investigation summaries
- investigation timelines
- investigation history
- backward-compatible analyze/investigate/build_timeline APIs

The current registry is intentionally in-memory. Persistent
investigation state belongs to the repository/database layer.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from services.intelligence.threat_intelligence.ioc_extractor import IOCExtractor


class AutonomousInvestigationIntelligenceEngine:
    """
    Autonomous investigation intelligence engine.

    This class is the canonical runtime implementation.

    Responsibilities:
    - create and track investigations
    - analyze investigation evidence
    - correlate threat activity
    - generate investigation summaries
    - generate investigation timelines
    - expose investigation history
    - preserve the original analyze/investigate/build_timeline API
    """

    def __init__(self) -> None:
        """Initialize an empty investigation registry."""
        self.investigations: list[dict[str, Any]] = []
        self.ioc_extractor = IOCExtractor()

    @staticmethod
    def _now() -> str:
        """Return the current UTC timestamp in ISO-8601 format."""
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _validate_investigation_id(
        investigation_id: str,
    ) -> None:
        """Validate an investigation identifier."""
        if not isinstance(investigation_id, str):
            raise TypeError(
                "Investigation ID must be a string."
            )

        if not investigation_id.strip():
            raise ValueError(
                "Investigation ID is required."
            )

    @staticmethod
    def _validate_sequence(
        value: Any,
        field_name: str,
    ) -> None:
        """Validate a list-like public API input."""
        if isinstance(value, (str, bytes)):
            raise TypeError(
                f"{field_name} must be a sequence of values, "
                "not a string."
            )

        if not isinstance(
            value,
            (list, tuple, set),
        ):
            raise TypeError(
                f"{field_name} must be a list, tuple, or set."
            )

    def _find_investigation(
        self,
        investigation_id: str,
    ) -> dict[str, Any] | None:
        """Return an internal investigation record if it exists."""
        for investigation in self.investigations:
            if (
                investigation.get("investigation_id")
                == investigation_id
            ):
                return investigation

        return None

    def create_investigation(
        self,
        investigation_id: str,
        investigation_type: str,
        severity: str,
    ) -> dict[str, Any]:
        """
        Create and register a new investigation.
        """
        self._validate_investigation_id(
            investigation_id
        )

        if not isinstance(
            investigation_type,
            str,
        ):
            raise TypeError(
                "Investigation type must be a string."
            )

        if not investigation_type.strip():
            raise ValueError(
                "Investigation type is required."
            )

        if not isinstance(
            severity,
            str,
        ):
            raise TypeError(
                "Severity must be a string."
            )

        if not severity.strip():
            raise ValueError(
                "Severity is required."
            )

        existing = self._find_investigation(
            investigation_id
        )

        if existing is not None:
            raise ValueError(
                f"Investigation "
                f"'{investigation_id}' already exists."
            )

        timestamp = self._now()

        investigation = {
            "investigation_id": investigation_id,
            "type": investigation_type,
            "severity": severity,
            "status": "active",
            "evidence": [],
            "evidence_count": 0,
            "threat_activity": [],
            "risk_level": "UNKNOWN",
            "timeline": [],
            "summary": None,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        self.investigations.append(
            investigation
        )

        return deepcopy(investigation)

    def analyze_evidence(
        self,
        investigation_id: str,
        evidence: list[Any],
    ) -> dict[str, Any]:
        """
        Analyze and register evidence for an investigation.
        """
        self._validate_investigation_id(
            investigation_id
        )

        self._validate_sequence(
            evidence,
            "Evidence",
        )

        investigation = self._find_investigation(
            investigation_id
        )

        if investigation is None:
            raise KeyError(
                f"Investigation "
                f"'{investigation_id}' was not found."
            )

        normalized_evidence = list(evidence)
        timestamp = self._now()

        investigation["evidence"] = deepcopy(
            normalized_evidence
        )

        investigation["evidence_count"] = len(
            normalized_evidence
        )

        investigation["updated_at"] = timestamp

        result = {
            "investigation_id": investigation_id,
            "evidence": deepcopy(
                normalized_evidence
            ),
            "evidence_count": len(
                normalized_evidence
            ),
            "status": "completed",
            "created_at": timestamp,
        }

        return result

    def correlate_threat_activity(
        self,
        indicators: list[Any],
    ) -> dict[str, Any]:
        """
        Correlate supplied threat activity indicators.

        The deterministic baseline treats the presence of
        indicators as high-risk activity. A future threat
        intelligence correlation engine can replace this
        implementation without changing the public contract.
        """
        self._validate_sequence(
            indicators,
            "Indicators",
        )

        normalized_indicators = list(indicators)

        risk_level = (
            "HIGH"
            if normalized_indicators
            else "LOW"
        )

        timestamp = self._now()

        result = {
            "indicators": deepcopy(
                normalized_indicators
            ),
            "indicator_count": len(
                normalized_indicators
            ),
            "risk_level": risk_level,
            "status": "completed",
            "created_at": timestamp,
        }

        return result

    def generate_investigation_summary(
        self,
        investigation_id: str,
    ) -> dict[str, Any]:
        """Generate a deterministic investigation summary."""
        self._validate_investigation_id(
            investigation_id
        )

        investigation = self._find_investigation(
            investigation_id
        )

        if investigation is None:
            raise KeyError(
                f"Investigation "
                f"'{investigation_id}' was not found."
            )

        evidence_count = investigation.get(
            "evidence_count",
            0,
        )

        summary = (
            f"Investigation {investigation_id} is "
            f"an active "
            f"{investigation.get('type', 'unknown')} "
            f"investigation with "
            f"{evidence_count} evidence item(s)."
        )

        timestamp = self._now()

        investigation["summary"] = summary
        investigation["updated_at"] = timestamp

        return {
            "investigation_id": investigation_id,
            "summary": summary,
            "status": "completed",
            "created_at": timestamp,
        }

    def generate_timeline(
        self,
        investigation_id: str,
    ) -> dict[str, Any]:
        """
        Generate the baseline investigation lifecycle timeline.
        """
        self._validate_investigation_id(
            investigation_id
        )

        investigation = self._find_investigation(
            investigation_id
        )

        if investigation is None:
            raise KeyError(
                f"Investigation "
                f"'{investigation_id}' was not found."
            )

        timestamp = self._now()

        events = [
            {
                "order": 1,
                "event": "investigation_created",
            },
            {
                "order": 2,
                "event": "evidence_analysis",
            },
            {
                "order": 3,
                "event": "threat_assessment",
            },
        ]

        investigation["timeline"] = deepcopy(
            events
        )

        investigation["updated_at"] = timestamp

        return {
            "investigation_id": investigation_id,
            "events": deepcopy(events),
            "status": "completed",
            "created_at": timestamp,
        }

    def get_investigation_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return detached copies of all investigations.
        """
        return deepcopy(
            self.investigations
        )

    def analyze(
        self,
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Analyze a raw evidence object.

        Preserves the original public API.
        """
        if not isinstance(
            evidence,
            dict,
        ):
            raise TypeError(
                "Evidence must be a dictionary."
            )

        analysis = {
            "type": "evidence_analysis",
            "input": deepcopy(evidence),
            "findings": [],
            "severity": evidence.get(
                "severity",
                "unknown",
            ),
            "status": "completed",
            "created_at": self._now(),
        }

        if evidence.get("event"):
            analysis["findings"].append(
                f"Detected event: "
                f"{evidence['event']}"
            )

        self.investigations.append(
            deepcopy(analysis)
        )

        return analysis

    def investigate(
        self,
        alert: Any,
        artifacts: list[Any] | None = None,
        iocs: list[Any] | None = None,
    ) -> dict[str, Any]:
        """
        Investigate a raw alert.

        Preserves the original public API.
        """
        evidence = list(artifacts or [])
        extracted_iocs: list[dict[str, Any]] = []
        for item in evidence:
            extracted_iocs.extend(self.ioc_extractor.extract(item))

        for item in iocs or []:
            if isinstance(item, dict):
                value = item.get("value") or item.get("indicator")
                if value:
                    extracted_iocs.append({
                        "type": item.get("type", "unknown"),
                        "value": str(value),
                    })
            elif item:
                extracted_iocs.append({"type": "unknown", "value": str(item)})

        unique_iocs = []
        seen = set()
        for indicator in extracted_iocs:
            value = indicator["value"]
            if value not in seen:
                seen.add(value)
                unique_iocs.append(indicator)

        text = " ".join(str(item).lower() for item in evidence)
        findings = []
        recommendations = []
        if "failed login" in text or "authentication failure" in text:
            findings.append("Multiple failed authentication attempts detected")
            recommendations.append("Check authentication logs")
        if unique_iocs:
            findings.append("Suspicious external IP observed")
            recommendations.extend([
                "Investigate source IP reputation",
                "Review affected account activity",
            ])
        if any(word in text for word in ("suspicious", "malicious", "credential")):
            findings.append("Possible credential access activity")

        mitre = ["T1110"] if "failed login" in text or "authentication failure" in text else []
        risk_score = min(100, len(unique_iocs) * 30 + (35 if findings else 0))
        confidence = min(1.0, 0.5 + (0.15 * len(findings)))
        attack_story = (
            "Authentication activity involving suspicious indicators was observed."
            if findings
            else None
        )

        investigation = {
            "type": "investigation",
            "alert": deepcopy(alert),
            "steps": [
                "alert_received",
                "indicator_analysis",
                "threat_assessment",
            ],
            "status": "completed",
            "findings": findings,
            "recommendations": list(dict.fromkeys(recommendations)),
            "iocs": unique_iocs,
            "risk_score": risk_score,
            "confidence": confidence,
            "mitre": mitre,
            "attack_story": attack_story,
            "created_at": self._now(),
        }

        self.investigations.append(
            deepcopy(investigation)
        )

        return investigation

    def build_timeline(
        self,
        events: list[Any],
    ) -> dict[str, Any]:
        """
        Build a timeline from arbitrary events.

        Preserves the original public API.
        """
        self._validate_sequence(
            events,
            "Events",
        )

        timeline = {
            "type": "timeline",
            "events": [],
            "status": "completed",
            "created_at": self._now(),
        }

        for index, event in enumerate(events):
            timeline["events"].append(
                {
                    "order": index + 1,
                    "event": deepcopy(event),
                }
            )

        return timeline
