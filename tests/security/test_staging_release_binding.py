"""Security tests for the external staging release-binding custody record."""

from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest

from services.auth.staging_release_binding import (
    SCHEMA_VERSION,
    StagingReleaseBindingError,
    load_release_binding,
    validate_release_binding,
)


def _manifest(**overrides):
    value = {
        "schema_version": SCHEMA_VERSION,
        "release_id": "test-release",
        "environment": "staging",
        "repository": "https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA.git",
        "commit": "0f734c3341799b93e8a66397f1a1da782fd3869d",
        "tree": "42ba7a2e55a88029df2f9af0ea1812696a9d05ea",
        "image_repository": "staging-app",
        "image_digest": "sha256:" + "1" * 64,
        "database_target_identity": "postgresql://sentinel@postgres:5432/sentinel_dna",
        "created_at": "2026-09-24T00:00:00Z",
        "expires_at": "2099-09-24T00:00:00Z",
    }
    value.update(overrides)
    unsigned = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    value["manifest_hash"] = hashlib.sha256(unsigned).hexdigest()
    return value


def _install(tmp_path, monkeypatch, manifest):
    manifest_path = tmp_path / "binding.json"
    trust_path = tmp_path / "trusted.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    trust_path.write_text(json.dumps({
        "schema_version": SCHEMA_VERSION,
        "manifest_hash": manifest["manifest_hash"],
        "commit": manifest["commit"],
        "tree": manifest["tree"],
        "image_digest": manifest["image_digest"],
    }), encoding="utf-8")
    monkeypatch.setenv("SENTINEL_DNA_RELEASE_BINDING_MANIFEST_FILE", str(manifest_path))
    monkeypatch.setenv("SENTINEL_DNA_RELEASE_BINDING_TRUST_FILE", str(trust_path))


def test_current_external_binding_is_accepted():
    manifest = _manifest()
    assert validate_release_binding(manifest)["image_digest"].startswith("sha256:")


@pytest.mark.parametrize("field,value", [
    ("commit", "e5a71f16a56e2cddf7c4c3c3295aaa53eee10f38"),
    ("tree", "8577fadc6c1dedb665f57f0c82378f4613d71a1e"),
    ("image_digest", "sha256:" + "b" * 64),
    ("environment", "production"),
])
def test_wrong_release_identity_is_rejected(field, value):
    manifest = _manifest()
    tampered = dict(manifest, **{field: value})
    with pytest.raises(StagingReleaseBindingError):
        validate_release_binding(tampered)


def test_expired_manifest_is_rejected():
    manifest = _manifest(created_at="2019-01-01T00:00:00Z", expires_at="2020-01-01T00:00:00Z")
    with pytest.raises(StagingReleaseBindingError, match="manifest_expired"):
        validate_release_binding(manifest)


def test_tampered_manifest_and_unsigned_manifest_are_rejected(tmp_path, monkeypatch):
    manifest = _manifest()
    manifest["image_digest"] = "sha256:" + "2" * 64
    _install(tmp_path, monkeypatch, manifest)
    with pytest.raises(StagingReleaseBindingError, match="manifest_hash_mismatch"):
        load_release_binding()
    unsigned = _manifest()
    unsigned.pop("manifest_hash")
    with pytest.raises(StagingReleaseBindingError, match="manifest_fields_invalid"):
        validate_release_binding(unsigned)


def test_trusted_manifest_hash_is_independent(tmp_path, monkeypatch):
    manifest = _manifest()
    _install(tmp_path, monkeypatch, manifest)
    trust_path = tmp_path / "trusted.json"
    trust = json.loads(trust_path.read_text(encoding="utf-8"))
    trust["manifest_hash"] = "0" * 64
    trust_path.write_text(json.dumps(trust), encoding="utf-8")
    with pytest.raises(StagingReleaseBindingError, match="trusted_binding_mismatch"):
        load_release_binding()
