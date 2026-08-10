"""
Investigation pipeline models.
"""

from dataclasses import dataclass, field


@dataclass
class InvestigationPipelineResult:
    """
    Unified investigation intelligence output.
    """

    case_id: str

    findings: list = field(
        default_factory=list
    )

    metadata: dict = field(
        default_factory=dict
    )


    def add_finding(
        self,
        finding,
    ):

        self.findings.append(
            finding
        )


    def to_dict(self):

        findings = [
            item.to_dict()
            if hasattr(item, "to_dict")
            else item
            for item in self.findings
        ]

        return {
            "case_id": self.case_id,

            # Internal naming
            "findings": findings,

            # Compatibility API
            "results": findings,

            "metadata": self.metadata,

            "status": self.metadata.get(
                "status",
                "unknown",
            ),
        }


    def __getitem__(
        self,
        key,
    ):
        """
        Dictionary-style compatibility.
        """

        return self.to_dict()[key]


    def get(
        self,
        key,
        default=None,
    ):

        return self.to_dict().get(
            key,
            default,
        )