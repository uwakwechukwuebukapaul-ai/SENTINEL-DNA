"""
Runtime Intelligence Metrics

Tracks runtime intelligence execution
statistics.
"""

from dataclasses import dataclass, field



@dataclass
class RuntimeIntelligenceMetrics:
    """
    Runtime execution metrics.
    """


    executions: int = 0


    successful_executions: int = 0


    failed_executions: int = 0


    provider_calls: int = 0


    correlation_events: int = 0


    fusion_events: int = 0


    confidence_scores: list[float] = field(
        default_factory=list
    )



    def record_execution(
        self,
        success: bool,
    ):

        self.executions += 1


        if success:

            self.successful_executions += 1

        else:

            self.failed_executions += 1



    def record_provider(
        self,
    ):

        self.provider_calls += 1



    def record_correlation(
        self,
    ):

        self.correlation_events += 1



    def record_fusion(
        self,
    ):

        self.fusion_events += 1



    def record_confidence(
        self,
        confidence: float,
    ):

        self.confidence_scores.append(
            confidence
        )



    def summary(
        self,
    ):

        average_confidence = 0.0


        if self.confidence_scores:

            average_confidence = (

                sum(
                    self.confidence_scores
                )
                /
                len(
                    self.confidence_scores
                )

            )


        return {

            "executions":
                self.executions,

            "successful":
                self.successful_executions,

            "failed":
                self.failed_executions,

            "providers":
                self.provider_calls,

            "correlations":
                self.correlation_events,

            "fusion":
                self.fusion_events,

            "average_confidence":
                average_confidence,

        }