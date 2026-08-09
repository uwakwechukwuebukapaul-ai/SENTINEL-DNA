"""
Sentinel DNA MITRE ATT&CK Mapper Tests

Validates report-based and artifact-based
ATT&CK technique mapping.
"""

from __future__ import annotations


from services.intelligence.mitre.mitre_mapper import (
    MitreMapper,
)



def test_email_mapping():

    mapper = MitreMapper()


    result = mapper.map_artifact(
        {
            "type": "email",
        }
    )


    assert len(result) == 1


    assert (
        result[0]["technique_id"]
        ==
        "T1566.002"
    )


    assert (
        result[0]["technique_name"]
        ==
        "Phishing: Spearphishing Link"
    )


    assert (
        result[0]["tactic"]
        ==
        "Initial Access"
    )


    assert (
        result[0]["confidence"]
        ==
        90
    )



def test_file_mapping():

    mapper = MitreMapper()


    result = mapper.map_artifact(
        {
            "type": "file",
        }
    )


    assert (
        result[0]["technique_id"]
        ==
        "T1204.002"
    )


    assert (
        result[0]["tactic"]
        ==
        "Execution"
    )



def test_credential_mapping():

    mapper = MitreMapper()


    result = mapper.map_artifact(
        {
            "type": "credential",
        }
    )


    assert (
        result[0]["technique_id"]
        ==
        "T1555"
    )


    assert (
        result[0]["tactic"]
        ==
        "Credential Access"
    )



def test_unknown_artifact_returns_empty():

    mapper = MitreMapper()


    result = mapper.map_artifact(
        {
            "type": "unknown",
        }
    )


    assert result == []



def test_report_mapping():

    mapper = MitreMapper()


    result = mapper.map(
        {
            "threat_assessment":
                "credential_phishing",
        }
    )


    assert (
        result["technique_id"]
        ==
        "T1566.002"
    )


    assert (
        result["technique_name"]
        ==
        "Phishing: Spearphishing Link"
    )


    assert (
        result["tactic"]
        ==
        "Initial Access"
    )


    assert (
        result["confidence"]
        ==
        90
    )



def test_unknown_report_returns_default():

    mapper = MitreMapper()


    result = mapper.map(
        {
            "threat_assessment":
                "unknown_threat",
        }
    )


    assert (
        result["technique_id"]
        is None
    )


    assert (
        result["confidence"]
        ==
        0
    )