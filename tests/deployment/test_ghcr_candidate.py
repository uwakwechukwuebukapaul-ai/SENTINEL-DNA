from __future__ import annotations

import pytest

from deployment.scripts.ghcr_candidate import (
    CandidateVerificationError,
    EXPECTED_COMMAND,
    EXPECTED_SOURCE,
    IMAGE_NAME,
    resolve_manifest_digest,
    verify_image_inspect,
    write_verified_outputs,
)


DIGEST = "sha256:" + "1" * 64
IMAGE_ID = "sha256:" + "2" * 64
REVISION = "b4843dd6419c5dd70cb9430a0d4dd7bf39b6686f"
IMAGE_CREATED = "2026-10-20T02:16:31Z"
PACKAGE_CREATED = "2026-10-20T02:17:00Z"


def _inspect() -> dict:
    return {
        "Id": IMAGE_ID,
        "RepoDigests": [f"{IMAGE_NAME}@{DIGEST}"],
        "Config": {
            "User": "sentinel",
            "Cmd": list(EXPECTED_COMMAND),
            "Entrypoint": None,
            "WorkingDir": "/app",
            "ExposedPorts": {"5000/tcp": {}},
            "Env": [
                "PATH=/usr/local/bin:/usr/bin:/bin",
                "LANG=C.UTF-8",
                "PYTHONDONTWRITEBYTECODE=1",
                "PYTHONUNBUFFERED=1",
                "SENTINEL_DNA_ENV=__RUNTIME_ENV_REQUIRED__",
            ],
            "Labels": {
                "org.opencontainers.image.revision": REVISION,
                "com.sentinel-dna.git.revision.full": REVISION,
                "org.opencontainers.image.version": REVISION,
                "org.opencontainers.image.source": EXPECTED_SOURCE,
                "org.opencontainers.image.created": IMAGE_CREATED,
            },
        },
    }


def _verify(inspect_data=None, **overrides):
    args = {
        "digest": DIGEST,
        "revision": REVISION,
        "image_version": REVISION,
        "candidate_tree": "9" * 40,
        "image_created": IMAGE_CREATED,
        "package_created_at": PACKAGE_CREATED,
        "package_version_id": 123,
    }
    args.update(overrides)
    return verify_image_inspect(_inspect() if inspect_data is None else inspect_data, **args)


def test_explicit_image_version_must_match_revision():
    with pytest.raises(CandidateVerificationError, match="image version must match"):
        _verify(image_version="0" * 40)


def test_absent_candidate_digest_is_required_for_verified_resolution():
    assert resolve_manifest_digest({"digest": DIGEST}, DIGEST) == DIGEST
    with pytest.raises(CandidateVerificationError, match="does not match"):
        resolve_manifest_digest({"digest": "sha256:" + "3" * 64}, DIGEST)


def test_verified_candidate_metadata_is_bound_to_digest_and_full_revision():
    evidence = _verify()
    assert evidence["immutable_digest"] == DIGEST
    assert evidence["candidate_sha"] == REVISION
    assert evidence["candidate_tree"] == "9" * 40
    assert evidence["image_reference"] == f"{IMAGE_NAME}@{DIGEST}"


@pytest.mark.parametrize(
    "change, expected_error",
    [
        (lambda data: data["Config"]["Labels"].update({"org.opencontainers.image.revision": "0" * 40}), "provenance mismatch"),
        (lambda data: data["Config"]["Labels"].update({"org.opencontainers.image.version": "0" * 40}), "provenance mismatch"),
        (lambda data: data["Config"]["Labels"].update({"com.sentinel-dna.git.revision.full": "0" * 40}), "provenance mismatch"),
        (lambda data: data["Config"]["Labels"].update({"org.opencontainers.image.source": "https://example.invalid/source"}), "provenance mismatch"),
        (lambda data: data["Config"]["Labels"].update({"org.opencontainers.image.created": "2026-10-20T02:38:42Z"}), "provenance mismatch"),
        (lambda data: data["Config"].update({"Cmd": ["sh"]}), "runtime command"),
        (lambda data: data["Config"].update({"User": "root"}), "runtime user"),
        (lambda data: data["Config"].update({"ExposedPorts": {"22/tcp": {}}}), "exposed ports"),
        (lambda data: data["Config"].update({"Entrypoint": ["/bin/sh"]}), "entrypoint"),
    ],
)
def test_wrong_revision_source_creation_or_runtime_metadata_fails(change, expected_error):
    inspect_data = _inspect()
    change(inspect_data)
    with pytest.raises(CandidateVerificationError, match=expected_error):
        _verify(inspect_data)


def test_missing_provenance_and_package_creation_metadata_fail_closed():
    inspect_data = _inspect()
    del inspect_data["Config"]["Labels"]["org.opencontainers.image.source"]
    with pytest.raises(CandidateVerificationError, match="provenance mismatch"):
        _verify(inspect_data)
    with pytest.raises(CandidateVerificationError, match="package creation metadata"):
        _verify(package_created_at="")
    with pytest.raises(CandidateVerificationError, match="package version provenance"):
        _verify(package_version_id=0)


def test_wrong_digest_reference_fails_even_if_image_configuration_matches():
    inspect_data = _inspect()
    inspect_data["RepoDigests"] = [f"{IMAGE_NAME}@sha256:{'4' * 64}"]
    with pytest.raises(CandidateVerificationError, match="does not resolve"):
        _verify(inspect_data)


def test_release_evidence_excludes_secret_values(tmp_path):
    secret = "never-serialize-this-value"
    evidence = _verify()
    evidence_path = tmp_path / "provenance.json"
    github_env = tmp_path / "github-env"
    write_verified_outputs(evidence, evidence_path=evidence_path, github_env=github_env)
    assert secret not in evidence_path.read_text()
    assert secret not in github_env.read_text()
    assert "SENTINEL_DNA_SECRET_KEY" not in evidence_path.read_text()
    assert "POSTGRES_PASSWORD" not in evidence_path.read_text()


def test_runtime_secret_environment_is_rejected_without_echoing_value(capsys):
    inspect_data = _inspect()
    inspect_data["Config"]["Env"].append("POSTGRES_PASSWORD=synthetic-secret-value")
    with pytest.raises(CandidateVerificationError, match="protected configuration") as error:
        _verify(inspect_data)
    assert "synthetic-secret-value" not in str(error.value)
    assert "synthetic-secret-value" not in capsys.readouterr().out
