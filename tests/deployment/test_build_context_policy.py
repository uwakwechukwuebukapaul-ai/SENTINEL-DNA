from __future__ import annotations

from pathlib import Path

import pytest

from deployment.scripts.build_context_policy import (
    REQUIRED_DOCKERIGNORE_RULES,
    dockerignore_rules,
    is_sensitive_build_context_path,
    matching_rules,
    validate_policy,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_checked_in_dockerignore_has_complete_sensitive_artifact_policy() -> None:
    assert validate_policy(REPOSITORY_ROOT) == ()
    assert set(REQUIRED_DOCKERIGNORE_RULES) <= dockerignore_rules(REPOSITORY_ROOT / ".dockerignore")


@pytest.mark.parametrize(
    "relative_path",
    (
        ".env", ".env.local", ".env.production", ".env.test",
        "production.env", "production.env.local", "nested/.env.production",
        "secret.pem", "private.key", "certificate.p12", "nested/certificate.pfx",
        "nested/secret/config.json", "nested/credentials/token.json",
    ),
)
def test_sensitive_sentinel_names_are_covered_without_real_secrets(relative_path: str) -> None:
    rules = dockerignore_rules(REPOSITORY_ROOT / ".dockerignore")
    assert is_sensitive_build_context_path(relative_path)
    assert matching_rules(relative_path, rules)


def test_legitimate_credentials_source_module_is_not_classified_as_an_artifact() -> None:
    assert not is_sensitive_build_context_path("services/integration_hub/credentials.py")
