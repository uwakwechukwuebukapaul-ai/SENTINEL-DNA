from __future__ import annotations

from pathlib import Path

import pytest

from deployment.aws.b3_disposable_integration.build_disposable_package import DisposableBuildError, build_package, validate_source
from deployment.aws.b3_disposable_integration.disposable_provider_config import (
    DisposableProviderConfig,
    config_from_mapping,
)
from deployment.aws.b3_disposable_integration.safety import SafetyError
from deployment.aws.b3_disposable_integration.build_disposable_package import SOURCE_FILES


def provider_values() -> dict[str, str]:
    return {
        "SENTINEL_DNA_DISPOSABLE_AWS_ACCOUNT_ID": "123456789012",
        "SENTINEL_DNA_DISPOSABLE_AWS_REGION": "eu-west-1",
        "SENTINEL_DNA_DISPOSABLE_PROVIDER_ENVIRONMENT": "sentinel-dna-b3-disposable-unit1234",
        "SENTINEL_DNA_DISPOSABLE_TABLE_NAME": "sentinel-dna-b3-disposable-unit1234-custody",
        "SENTINEL_DNA_DISPOSABLE_EVIDENCE_BUCKET": "sentinel-dna-b3-disposable-unit1234-evidence",
        "SENTINEL_DNA_DISPOSABLE_KMS_KEY_ARN": "arn:aws:kms:eu-west-1:123456789012:key/11111111-1111-1111-1111-111111111111",
        "SENTINEL_DNA_DISPOSABLE_FUNCTION_NAME": "sentinel-dna-b3-disposable-unit1234-provider",
        "SENTINEL_DNA_DISPOSABLE_ROLE_NAME": "sentinel-dna-b3-disposable-unit1234-provider",
    }


def test_disposable_provider_config_rejects_trust_identifiers() -> None:
    values = provider_values()
    values["SENTINEL_DNA_DISPOSABLE_TABLE_NAME"] = "SentinelDNA-Trust-ReplayCustody"
    with pytest.raises(SafetyError):
        config_from_mapping(values)


def test_disposable_provider_config_rejects_trust_account() -> None:
    values = provider_values()
    values["SENTINEL_DNA_DISPOSABLE_AWS_ACCOUNT_ID"] = "634176594969"
    with pytest.raises(SafetyError):
        config_from_mapping(values)


def test_disposable_provider_config_rejects_trust_bucket_and_key() -> None:
    values = provider_values()
    values["SENTINEL_DNA_DISPOSABLE_EVIDENCE_BUCKET"] = "sentinel-dna-trust-evidence-634176594969-eu-west-1"
    with pytest.raises(SafetyError):
        config_from_mapping(values)


def test_disposable_environment_is_explicit_and_parameterized() -> None:
    config = config_from_mapping(provider_values())
    assert config.environment_variables()["SENTINEL_DNA_REPLAY_CUSTODY_TABLE"] == config.table_name
    assert config.environment_variables()["SENTINEL_DNA_REPLAY_EVIDENCE_BUCKET"] == config.evidence_bucket
    assert config.environment_variables()["SENTINEL_DNA_REPLAY_KMS_KEY_ID"] == config.kms_key_arn
    assert config.contract()["contract"] == "sentinel-dna-b3-disposable-provider-v1"


def test_current_trust_pinned_source_is_refused() -> None:
    source_root = Path("sentinel-dna-gate-b2-c320b25")
    with pytest.raises(DisposableBuildError, match="Trust-pinned"):
        validate_source(source_root)


def test_deterministic_package_and_provenance(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    for relative in (
        "services/__init__.py",
        "services/auth/__init__.py",
        "services/auth/custody_binding.py",
        "services/auth/external_replay_custody.py",
        "services/auth/custody_provider_boundary.py",
    ):
        target = source_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# disposable-provider-source\n", encoding="utf-8")
    config = config_from_mapping(provider_values())
    zip_one, zip_two = tmp_path / "one.zip", tmp_path / "two.zip"
    manifest_one, manifest_two = tmp_path / "one.json", tmp_path / "two.json"
    first = build_package(source_root, zip_one, manifest_one, "source-revision-1", config)
    second = build_package(source_root, zip_two, manifest_two, "source-revision-1", config)
    assert zip_one.read_bytes() == zip_two.read_bytes()
    assert first == second


def test_committed_disposable_provider_source_is_buildable(tmp_path: Path) -> None:
    source_root = Path("deployment/aws/b3_disposable_integration/provider_source")
    source_hashes = validate_source(source_root)
    assert tuple(source_hashes) == SOURCE_FILES
    config = config_from_mapping(provider_values())
    manifest = build_package(
        source_root,
        tmp_path / "provider.zip",
        tmp_path / "provider-manifest.json",
        "offline-test-revision",
        config,
    )
    assert manifest["source_revision"] == "offline-test-revision"
    assert manifest["configuration_contract"]["contract"] == "sentinel-dna-b3-disposable-provider-v1"


def test_disposable_runtime_contract_is_explicit() -> None:
    config = config_from_mapping(provider_values())
    runtime = config.environment_variables()
    assert runtime["SENTINEL_DNA_DISPOSABLE_PROVIDER"] == "sentinel-dna-b3-disposable-provider-v1"
    assert runtime["SENTINEL_DNA_DISPOSABLE_AWS_ACCOUNT_ID"] == "123456789012"
    assert runtime["SENTINEL_DNA_DISPOSABLE_TABLE_NAME"] == config.table_name
    assert runtime["SENTINEL_DNA_DISPOSABLE_EVIDENCE_BUCKET"] == config.evidence_bucket
    assert runtime["SENTINEL_DNA_DISPOSABLE_KMS_KEY_ARN"] == config.kms_key_arn


def test_disposable_provider_preserves_contract_operations() -> None:
    source = Path("deployment/aws/b3_disposable_integration/provider_source/services/auth/custody_provider_boundary.py").read_text(encoding="utf-8")
    for operation in ("RESERVE", "RECONCILE", "INSPECT", "VERIFY", "CONSUME", "ABORT"):
        assert operation in source
