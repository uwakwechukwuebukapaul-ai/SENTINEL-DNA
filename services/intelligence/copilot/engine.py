"""
Sentinel DNA AI SOC Copilot Engine.

Transforms structured investigation intelligence
into analyst-facing explanations and recommendations.

The initial implementation is deterministic and
provider-independent. LLM providers can be added
through an adapter without changing this contract.
"""

from typing import Any

from .models import (
    CopilotResponse,
)


class AISocCopilot:
    """
    Analyst-facing AI SOC Copilot.
    """

    def explain(
        self,
        case_id: str,
        investigation: Any = None,
        question: str | None = None,
    ) -> CopilotResponse:
        """
        Explain an investigation to a SOC analyst.
        """

        data = self._normalize(
            investigation
        )

        risk = self._normalize_risk(
            data.get(
                "risk",
                "unknown",
            )
        )

        confidence = self._normalize_confidence(
            data.get(
                "confidence",
                0,
            )
        )

        findings = self._normalize_list(
            data.get(
                "findings",
                [],
            )
        )

        recommendations = self._unique_strings(
            data.get(
                "recommendations",
                [],
            )
        )

        mitre = self._unique_strings(
            data.get(
                "mitre_techniques",
                [],
            )
        )

        answer = self._build_answer(
            risk=risk,
            confidence=confidence,
            findings=findings,
            mitre=mitre,
            question=question,
        )

        if not recommendations:
            recommendations = self._default_actions(
                risk
            )

        return CopilotResponse(
            case_id=case_id,
            answer=answer,
            risk=risk,
            confidence=confidence,
            evidence_used=findings,
            recommended_actions=recommendations,
            mitre_techniques=mitre,
            metadata={
                "engine": "ai_soc_copilot",
                "question_provided": bool(
                    question
                ),
                "finding_count": len(
                    findings
                ),
                "mitre_count": len(
                    mitre
                ),
            },
        )

    def ask(
        self,
        case_id: str,
        question: str,
        investigation: Any = None,
    ) -> CopilotResponse:
        """
        Answer an analyst question using investigation context.
        """

        return self.explain(
            case_id=case_id,
            investigation=investigation,
            question=question,
        )

    def _normalize(
        self,
        investigation: Any,
    ) -> dict[str, Any]:
        """
        Normalize dictionary and dataclass investigation objects.
        """

        if investigation is None:
            return {}

        if isinstance(
            investigation,
            dict,
        ):
            return dict(
                investigation
            )

        to_dict = getattr(
            investigation,
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
                return result

        attributes = (
            "case_id",
            "risk",
            "confidence",
            "findings",
            "mitre_techniques",
            "recommendations",
            "metadata",
        )

        return {
            name: getattr(
                investigation,
                name,
                None,
            )
            for name in attributes
        }

    def _normalize_risk(
        self,
        risk: Any,
    ) -> str:
        """
        Normalize investigation risk.
        """

        value = str(
            risk or "unknown"
        ).lower().strip()

        allowed = {
            "critical",
            "high",
            "medium",
            "low",
            "unknown",
        }

        if value in allowed:
            return value

        return "unknown"

    def _normalize_confidence(
        self,
        confidence: Any,
    ) -> int:
        """
        Normalize confidence into 0-100.
        """

        try:
            value = int(
                confidence
            )

        except (
            TypeError,
            ValueError,
        ):
            return 0

        return max(
            0,
            min(
                100,
                value,
            ),
        )

    def _normalize_list(
        self,
        values: Any,
    ) -> list[Any]:
        """
        Normalize collection values.
        """

        if values is None:
            return []

        if isinstance(
            values,
            list,
        ):
            return list(
                values
            )

        if isinstance(
            values,
            tuple,
        ):
            return list(
                values
            )

        return [
            values
        ]

    def _unique_strings(
        self,
        values: Any,
    ) -> list[str]:
        """
        Normalize and deduplicate string collections.
        """

        result = []

        for value in self._normalize_list(
            values
        ):
            text = str(
                value
            ).strip()

            if (
                text
                and text not in result
            ):
                result.append(
                    text
                )

        return result

    def _build_answer(
        self,
        risk: str,
        confidence: int,
        findings: list[Any],
        mitre: list[str],
        question: str | None,
    ) -> str:
        """
        Build deterministic analyst explanation.
        """

        finding_count = len(
            findings
        )

        mitre_count = len(
            mitre
        )

        if risk in {
            "critical",
            "high",
        }:
            posture = (
                "The investigation indicates "
                "elevated security risk and "
                "requires analyst attention."
            )

        elif risk == "medium":
            posture = (
                "The investigation indicates "
                "suspicious activity that "
                "requires further validation."
            )

        elif risk == "low":
            posture = (
                "The investigation currently "
                "shows no immediate high-risk "
                "threat."
            )

        else:
            posture = (
                "The investigation risk level "
                "could not be confidently classified."
            )

        answer = (
            f"{posture} "
            f"The investigation contains "
            f"{finding_count} finding(s), "
            f"{mitre_count} MITRE ATT&CK "
            f"mapping(s), and a confidence "
            f"level of {confidence}%."
        )

        if question:
            answer += (
                f" Analyst question addressed: "
                f"{question.strip()}"
            )

        return answer

    def _default_actions(
        self,
        risk: str,
    ) -> list[str]:
        """
        Generate safe baseline analyst actions.
        """

        if risk in {
            "critical",
            "high",
        }:
            return [
                "Validate affected entities",
                "Collect supporting telemetry",
                "Review related indicators",
                "Initiate incident response",
            ]

        if risk == "medium":
            return [
                "Perform additional investigation",
                "Validate suspicious indicators",
                "Monitor affected entities",
            ]

        return [
            "Continue monitoring",
            "Maintain evidence collection",
        ]