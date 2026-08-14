from __future__ import annotations

def metric(expected, actual) -> float:
    expected = set(expected or [])
    actual = set(actual or [])
    return 1.0 if not expected else round(len(expected & actual) / len(expected), 2)

def score_investigation(expected: dict, result: dict) -> dict:
    findings = result.get("findings", [])
    recommendations = result.get("recommendations", [])
    mitre = result.get("mitre", result.get("mitre_techniques", []))
    evidence = result.get("artifacts", []) or result.get("evidence", [])
    expected_findings = expected.get("expected_findings", [])
    findings_text = " ".join(str(item).lower() for item in findings)
    finding_accuracy = round(sum(str(item).lower() in findings_text for item in expected_findings) / len(expected_findings), 2) if expected_findings else 1.0
    breakdown = {
        "evidence_coverage": 1.0 if evidence else 0.0,
        "finding_accuracy": finding_accuracy,
        "mitre_mapping": metric(expected.get("expected_mitre"), mitre),
        "recommendation_quality": 1.0 if recommendations else 0.0,
        "explainability": 1.0 if result.get("attack_story") else 0.0,
    }
    return {"score": round(sum(breakdown.values()) / len(breakdown) * 100, 2), "metrics": breakdown}
