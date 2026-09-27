from __future__ import annotations

import json

import pytest

from deployment.aws.b3_disposable_integration.evidence import canonical_evidence
from deployment.aws.b3_disposable_integration.safety import (
    ACCOUNT_ACK,
    ACCOUNT_ENV,
    PREFIX_ENV,
    REGION_ENV,
    RESOURCE_ACK,
    RESOURCE_ACK_VALUE,
    RUN_FLAG,
    ACK_VALUE,
    SafetyError,
    assert_safe_name,
    load_config,
    verify_caller_account,
)


def valid_env() -> dict[str, str]:
    return {
        RUN_FLAG: "1",
        ACCOUNT_ACK: ACK_VALUE,
        RESOURCE_ACK: RESOURCE_ACK_VALUE,
        ACCOUNT_ENV: "123456789012",
        REGION_ENV: "eu-west-1",
        PREFIX_ENV: "sentinel-dna-b3-disposable-unit1234",
        "SENTINEL_DNA_DISPOSABLE_RUN_ID": "abc12345def6",
    }


def test_missing_opt_in_refuses() -> None:
    env = valid_env()
    del env[RUN_FLAG]
    with pytest.raises(SafetyError):
        load_config(env)


def test_missing_account_refuses() -> None:
    env = valid_env()
    del env[ACCOUNT_ENV]
    with pytest.raises(SafetyError):
        load_config(env)


def test_trust_account_refuses() -> None:
    env = valid_env()
    env[ACCOUNT_ENV] = "634176594969"
    with pytest.raises(SafetyError):
        load_config(env)


def test_mismatched_sts_account_refuses() -> None:
    config = load_config(valid_env())
    class Sts:
        def get_caller_identity(self):
            return {"Account": "999999999999", "Arn": "arn:aws:sts::999999999999:assumed-role/test/x"}
    with pytest.raises(SafetyError):
        verify_caller_account(Sts(), config)


def test_unsafe_prefix_refuses() -> None:
    env = valid_env()
    env[PREFIX_ENV] = "sentinel-dna-trust-evidence-634176594969-eu-west-1"
    with pytest.raises(SafetyError):
        load_config(env)


def test_generated_names_are_unique_and_scoped() -> None:
    config = load_config(valid_env())
    assert len(set(config.names.values())) == len(config.names)
    assert all(name.startswith(f"{config.resource_prefix}-{config.run_id}-") for name in config.names.values() if not name.startswith("alias/"))
    assert_safe_name(config.names["table"], config)


def test_cleanup_scope_rejects_untracked_name() -> None:
    config = load_config(valid_env())
    with pytest.raises(SafetyError):
        assert_safe_name("other-account-resource", config)


def test_evidence_rejects_secrets() -> None:
    with pytest.raises(ValueError):
        canonical_evidence({"access_key_id": "never-store"})


def test_evidence_is_canonical_and_safe() -> None:
    raw = {"resource": "arn:aws:dynamodb:eu-west-1:123456789012:table/x", "status": "PASS"}
    encoded = canonical_evidence(raw)
    assert json.loads(encoded) == raw
    assert b"secret" not in encoded.lower()

