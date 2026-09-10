"""Single source of truth for pilot scenario identifiers."""

from __future__ import annotations


APPROVED_SCENARIO_IDENTIFIERS = frozenset(
    {
        "phishing_compromise",
        "credential_theft",
        "malware_execution",
        "suspicious_authentication",
        "lateral_movement",
        "command_and_control",
        "benign_false_positive",
        "multi_ioc_investigation",
        "suspicious_powershell_execution",
    }
)

# These are deliberately explicit.  ``None`` means no approved identifier
# exists and prevents callers from silently treating a fixture label as an
# approved pilot scenario.
REQUESTED_CATEGORY_IDENTIFIERS = {
    "suspicious_ip_domain": None,
    "phishing_url": None,
    "suspicious_authentication": "suspicious_authentication",
    "endpoint_compromise": None,
}

# Existing fixture association, not an approved literal category identifier.
EXISTING_FIXTURE_CATEGORY_MAPPINGS = {
    "malware_execution": "endpoint_compromise",
}


__all__ = [
    "APPROVED_SCENARIO_IDENTIFIERS",
    "EXISTING_FIXTURE_CATEGORY_MAPPINGS",
    "REQUESTED_CATEGORY_IDENTIFIERS",
]
