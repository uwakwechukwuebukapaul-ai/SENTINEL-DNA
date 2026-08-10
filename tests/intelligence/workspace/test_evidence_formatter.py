"""
Evidence Formatter Tests.

Validates evidence normalization.
"""

from services.intelligence.workspace.evidence_formatter import (
    EvidenceFormatter,
)



def create_formatter():

    return EvidenceFormatter()



def test_formatter_creation():

    formatter = create_formatter()

    assert formatter is not None



def test_format_domain_indicator():

    formatter = create_formatter()

    result = formatter.format(
        {
            "type": "domain",
            "value": "evil.com",
        }
    )

    assert result is not None



def test_format_ip_indicator():

    formatter = create_formatter()

    result = formatter.format(
        {
            "type": "ip",
            "value": "10.10.10.10",
        }
    )

    assert result is not None



def test_format_unknown_evidence():

    formatter = create_formatter()

    result = formatter.format(
        {
            "value": "unknown",
        }
    )

    assert result is not None



def test_format_empty_evidence():

    formatter = create_formatter()

    result = formatter.format({})

    assert result is not None