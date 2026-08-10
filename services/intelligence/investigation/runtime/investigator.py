"""
Sentinel DNA AI Investigator Runtime.

Coordinates the complete autonomous investigation lifecycle:

Evidence
    ↓
Correlation
    ↓
Reasoning
    ↓
Fusion
    ↓
Reporting

Execution layer for AI SOC investigations.
"""

from typing import Any


from ..correlation.analyzer import (
    EvidenceCorrelationAnalyzer,
)

from ..reasoning.engine import (
    InvestigationReasoningEngine,
)

from ..fusion.engine import (
    InvestigationFusionEngine,
)

from ..reporting.generator import (
    InvestigationReportGenerator,
)

from .models import (
    RuntimeResult,
)



class AIInvestigatorRuntime:
    """
    Main autonomous investigation runtime.
    """


    def __init__(self):

        self.correlation = (
            EvidenceCorrelationAnalyzer()
        )

        self.reasoning = (
            InvestigationReasoningEngine()
        )

        self.fusion = (
            InvestigationFusionEngine()
        )

        self.reporting = (
            InvestigationReportGenerator()
        )



    def investigate(
        self,
        case_id: str,
        evidence: Any,
    ) -> RuntimeResult:
        """
        Execute complete investigation workflow.
        """


        # -----------------------------
        # Correlation
        # -----------------------------

        correlation_result = (
            self.correlation.analyze(
                self._normalize_evidence(
                    evidence
                )
            )
        )


        findings = (
            correlation_result.findings
        )



        # -----------------------------
        # Reasoning
        # -----------------------------

        reasoning_result = (
            self.reasoning.analyze(
                findings
            )
        )



        # -----------------------------
        # Fusion
        # -----------------------------

        intelligence = (
            self.fusion.fuse(
                case_id=case_id,

                findings=findings,

                reasoning=reasoning_result,
            )
        )



        # -----------------------------
        # Reporting
        # -----------------------------

        report = (
            self.reporting.generate(
                intelligence,

                case_id=case_id,
            )
        )


        if hasattr(
            report,
            "to_dict",
        ):

            report_data = (
                report.to_dict()
            )

        else:

            report_data = report



        return RuntimeResult(

            case_id=case_id,

            status="completed",

            report=report_data,

            metadata={

                "engine":
                    "ai_investigator_runtime",


                "stages": [

                    "correlation",

                    "reasoning",

                    "fusion",

                    "reporting",

                ],


                "pipeline": [

                    "correlation",

                    "reasoning",

                    "fusion",

                    "reporting",

                ],


                "finding_count":
                    len(findings),


                "risk":
                    getattr(
                        reasoning_result,
                        "risk",
                        "unknown",
                    ),


                "confidence":
                    getattr(
                        reasoning_result,
                        "confidence",
                        0,
                    ),

            },
        )



    def _normalize_evidence(
        self,
        evidence,
    ):
        """
        Normalize incoming investigation evidence.
        """


        if isinstance(
            evidence,
            list,
        ):

            return evidence



        if isinstance(
            evidence,
            dict,
        ):

            return [

                {

                    "category":
                        "observed_artifact",


                    "value":
                        value,


                    "source":
                        key,


                    "evidence_type":
                        "runtime_input",

                }

                for key, value in evidence.items()

            ]



        return [

            evidence

        ]





class InvestigationRuntimeAPI:
    """
    Public runtime API boundary.

    Used by future Flask APIs,
    dashboards, SOAR workflows,
    and external integrations.
    """


    def __init__(self):

        self.runtime = (
            AIInvestigatorRuntime()
        )



    def investigate(
        self,
        case_id: str,
        evidence: Any,
    ):

        return self.runtime.investigate(
            case_id,

            evidence,
        )





class Investigator:
    """
    Compatibility investigator wrapper.
    """


    def __init__(self):

        self.runtime = (
            AIInvestigatorRuntime()
        )



    def investigate(
        self,
        case_id: str,
        evidence: Any,
    ):

        return self.runtime.investigate(
            case_id,

            evidence,
        )





class AIInvestigator(
    Investigator
):
    """
    Backward compatible AI Investigator.
    """

    pass





def investigate(
    case_id: str,
    evidence: Any,
):
    """
    Convenience runtime function.
    """


    runtime = (
        AIInvestigatorRuntime()
    )


    return runtime.investigate(
        case_id,

        evidence,
    )