"""Report-generation seam for the FAVP operations platform."""

from .service import FAVPOperationsService


class FAVPValidationReportGenerator:
    """Keep report generation explicit and read-only."""

    def __init__(self, operations: FAVPOperationsService) -> None:
        self.operations = operations

    def generate(self, *, tenant_id: str, generated_by: str) -> dict:
        return self.operations.report(tenant_id=tenant_id, generated_by=generated_by)


__all__ = ["FAVPValidationReportGenerator"]
