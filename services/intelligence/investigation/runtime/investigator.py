"""
Sentinel DNA AI Investigator Runtime.

Coordinates autonomous investigation execution.
"""


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
        evidence,
    ):

        correlation = (
            self.correlation.analyze(
                evidence
            )
        )


        findings = (
            correlation.findings
        )


        reasoning = (
            self.reasoning.analyze(
                findings
            )
        )


        intelligence = (
            self.fusion.fuse(
                case_id,
                findings,
                reasoning,
            )
        )


        report = (
            self.reporting.generate(
                intelligence
            )
        )


        return RuntimeResult(

            case_id=case_id,

            status="completed",

            report=(
                report.to_dict()
                if hasattr(
                    report,
                    "to_dict",
                )
                else report
            ),

            metadata={
                "engine":
                    "ai_investigator_runtime",
                "stages":[
                    "correlation",
                    "reasoning",
                    "fusion",
                    "reporting",
                ],
            },
        )