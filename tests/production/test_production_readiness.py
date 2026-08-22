from pathlib import Path

from services.core.observability import normalize_correlation_id
from services.core.production_readiness import assess_production_readiness


def test_readiness_report_is_conservative_and_machine_readable(tmp_path):
    (tmp_path / "production-readiness.md").write_text("ready", encoding="utf-8")
    (tmp_path / "security-architecture.md").write_text("security", encoding="utf-8")
    (tmp_path / "deployment.md").write_text("deploy", encoding="utf-8")
    (tmp_path / "operations-runbook.md").write_text("ops", encoding="utf-8")
    report = assess_production_readiness(
        environment="production",
        secure_cookies=True,
        debug=False,
        secret_configured=True,
        database_ok=True,
        required_services_ok=True,
        canonical_authority_ok=True,
        request_limits_configured=True,
        documentation_root=Path(tmp_path),
        external_checks={"deployment": "PASS", "browser": "PASS", "performance": "PASS"},
    )
    assert report["version"] == "production-readiness-v1"
    assert report["release_status"] == "PASS"
    assert report["classification"] == "PRODUCTION READY"
    assert all(item["status"] in {"PASS", "WARN", "BLOCKED", "FAIL"} for item in report["gates"])


def test_readiness_does_not_infer_external_checks():
    report = assess_production_readiness(
        environment="development",
        secure_cookies=False,
        debug=True,
        secret_configured=False,
        database_ok=True,
        required_services_ok=True,
        canonical_authority_ok=True,
        request_limits_configured=True,
    )
    assert report["release_status"] == "FAIL"
    assert "Deployment" in report["blocking_gates"]
    assert "Browser" in report["blocking_gates"]


def test_correlation_ids_are_bounded_and_header_safe():
    assert normalize_correlation_id("case-123/attempt-2") == "case-123/attempt-2"
    generated = normalize_correlation_id("bad\nX-Leak: yes")
    assert generated and "\n" not in generated and len(generated) <= 128


def test_deployment_cli_builds_a_report_without_external_inference():
    from deployment.production.readiness import build_report

    report = build_report()
    assert report["version"] == "production-readiness-v1"
    assert report["release_status"] in {"PASS", "WARN", "BLOCKED", "FAIL"}
    assert "Browser" in {item["name"] for item in report["gates"]}
