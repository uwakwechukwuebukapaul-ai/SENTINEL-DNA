from sentinel_dna.investigation.trace import InvestigationTrace


def attach_trace(context):
    """
    Attach investigation trace storage
    to the investigation context.
    """

    trace = InvestigationTrace(
        case_id=context.case_id
    )

    context.audit_trail = trace.events

    trace.add_event(
        "trace_initialized",
        "Investigation trace initialized.",
    )

    return trace
