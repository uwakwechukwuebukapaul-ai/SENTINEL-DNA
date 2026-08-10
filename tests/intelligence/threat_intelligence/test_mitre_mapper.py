"""
Tests for Sentinel DNA MITRE ATT&CK mapper.
"""

import sys
from pathlib import Path


# Ensure the repository root is available when tests are invoked directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from services.intelligence.threat_intelligence.mitre_mapper import (  # type: ignore[import-not-found]
    MITREMapper,
)


def test_phishing_mapping():

    mapper = MITREMapper()

    result = mapper.map(
        {
            "threat":
                "credential phishing email"
        }
    )

    assert len(result) == 2

    technique_ids = {
        item["technique_id"]
        for item in result
    }

    assert "T1566" in technique_ids
    assert "T1056" in technique_ids


def test_command_mapping():

    mapper = MITREMapper()

    result = mapper.map(
        {
            "activity":
                "command execution"
        }
    )

    assert len(result) == 1

    assert (
        result[0]["technique_id"]
        ==
        "T1059"
    )


def test_indicator_mapping():

    mapper = MITREMapper()

    result = mapper.map_indicator(
        {
            "type":
                "domain",

            "value":
                "credential-login.xyz",
        }
    )

    assert (
        result["technique_id"]
        ==
        "T1056"
    )

    assert (
        result["name"]
        ==
        "Input Capture"
    )

    assert (
        result["tactic"]
        ==
        "Collection"
    )


def test_unknown_indicator():

    mapper = MITREMapper()

    result = mapper.map_indicator(
        {
            "value":
                "normal-domain.com"
        }
    )

    assert (
        result["technique_id"]
        is None
    )

    assert (
        result["confidence"]
        ==
        0.0
    )