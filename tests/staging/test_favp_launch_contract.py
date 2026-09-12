from pathlib import Path
import json

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_staging_compose_exposes_only_opt_in_favp_and_disposable_evidence_volume():
    compose = yaml.safe_load((ROOT / "deployment" / "staging" / "docker-compose.yml").read_text(encoding="utf-8"))
    app = compose["services"]["app"]
    environment = app["environment"]
    assert environment["SENTINEL_DNA_FAVP_OPERATIONS_ENABLED"] == "${SENTINEL_DNA_FAVP_OPERATIONS_ENABLED:-0}"
    assert environment["SENTINEL_DNA_FAVP_SYNTHETIC_ONLY"] == "${SENTINEL_DNA_FAVP_SYNTHETIC_ONLY:-1}"
    assert environment["SENTINEL_DNA_FAVP_PRODUCTION_ACCESS"] == "0"
    assert environment["SENTINEL_DNA_FAVP_EVIDENCE_DIR"] == "/var/lib/sentinel/favp-evidence"
    assert "staging_favp_evidence:/var/lib/sentinel/favp-evidence" in app["volumes"]
    assert "staging_favp_evidence" in compose["volumes"]


def test_staging_postgres_provisioning_contract_remains_private_and_health_checked():
    compose = yaml.safe_load((ROOT / "deployment" / "staging" / "docker-compose.yml").read_text(encoding="utf-8"))
    postgres = compose["services"]["postgres"]
    assert postgres["image"] == "postgres:16-alpine"
    assert postgres["healthcheck"]
    assert "staging_internal" in postgres["networks"]
    assert compose["networks"]["staging_internal"]["internal"] is True


def test_first_run_package_is_non_provisioning_and_simulation_only():
    package = json.loads((ROOT / "deployment" / "staging" / "simulation" / "favp-first-run-package.json").read_text(encoding="utf-8"))
    assert package["mode"] == "NON_PRODUCTION_TEST_ONLY"
    assert package["simulation_only"] is True
    assert package["production_authorization"] is False
    assert package["credentials_stored"] is False
    assert package["customer_data_included"] is False
    assert all(item["provisioned"] is False for item in package["analyst_accounts"] + package["organizations"])
    assert package["validation_runs"][0]["status"] == "NOT_EXECUTED"
    assert package["validation_runs"][0]["results_recorded"] is False


def test_favp_activation_is_a_separate_confirmed_staging_command():
    script = (ROOT / "deployment" / "staging" / "scripts" / "activate_favp_participant.py").read_text(encoding="utf-8")
    assert "--operator-confirmation" in script
    assert "SENTINEL_DNA_ENV=staging" in script
    assert "SENTINEL_DNA_FAVP_PRODUCTION_ACCESS" in script
    assert "SENTINEL_DNA_TENANT_ISOLATION_ENABLED" in script
    assert "FAVPParticipantActivationService" in script
