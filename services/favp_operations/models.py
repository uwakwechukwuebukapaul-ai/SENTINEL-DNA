"""Stable FAVP domain constants.

The values are intentionally plain strings because records cross the database
and HTTP boundaries.  A caller must supply real participant and organization
records; this module never seeds people, companies, or outcomes.
"""

FAVP_PROGRAM_STATES = (
    "INVITED",
    "APPLIED",
    "SCREENING",
    "ACCEPTED",
    "ONBOARDING",
    "ACTIVE_VALIDATION",
    "COMPLETED",
    "DESIGN_PARTNER_CANDIDATE",
    "DECLINED",
    "REVOKED",
)

FAVP_VALIDATION_PHASES = (
    "PROGRAM_SCOPING",
    "SCREENING",
    "ONBOARDING",
    "BASELINE",
    "ACTIVE_VALIDATION",
    "CLOSEOUT",
)

FAVP_SCORES = (
    "trust_evidence",
    "reasoning_understanding",
    "confidence_rating",
    "provenance_clarity",
    "timeline_usefulness",
    "ioc_enrichment_usefulness",
    "evidence_quality",
)

FAVP_PROGRAM_STATE_TRANSITIONS = {
    "INVITED": {"APPLIED", "DECLINED", "REVOKED"},
    "APPLIED": {"SCREENING", "DECLINED", "REVOKED"},
    "SCREENING": {"ACCEPTED", "DECLINED", "REVOKED"},
    "ACCEPTED": {"ONBOARDING", "DECLINED", "REVOKED"},
    "ONBOARDING": {"ACTIVE_VALIDATION", "REVOKED"},
    "ACTIVE_VALIDATION": {"COMPLETED", "DESIGN_PARTNER_CANDIDATE", "REVOKED"},
    "COMPLETED": {"DESIGN_PARTNER_CANDIDATE", "REVOKED"},
    "DESIGN_PARTNER_CANDIDATE": {"REVOKED"},
    "DECLINED": set(),
    "REVOKED": set(),
}

__all__ = [
    "FAVP_PROGRAM_STATES",
    "FAVP_PROGRAM_STATE_TRANSITIONS",
    "FAVP_SCORES",
    "FAVP_VALIDATION_PHASES",
]
