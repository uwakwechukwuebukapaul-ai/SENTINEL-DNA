from sentinel_dna.investigation.context import InvestigationContext
from sentinel_dna.investigation.trace import InvestigationTrace


def attach_trace(
    context: InvestigationContext,
) -> InvestigationTrace:
    trace = InvestigationTrace(
        case_id=context.case_id
    )

    context.trace = trace
    context.audit_trail = trace.events

    return trace
