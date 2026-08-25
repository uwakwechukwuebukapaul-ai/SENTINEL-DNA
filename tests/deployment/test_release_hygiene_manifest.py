from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest

from deployment.scripts.release_manifest import (
    ReleaseManifestError,
    build_manifest,
    verify_manifest,
    write_manifest,
)
from deployment.validation.release_hygiene import ReleaseHygieneValidator


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _artifact(path: Path, commit_sha: str) -> Path:
    body = {
        "commit_sha": commit_sha,
        "immutable": True,
        "replay_digest": "replay-reference",
        "evidence_sources": [
            {
                "source": "enterprise_evidence_closure",
                "report_digest": "report-reference",
                "replay_digest": "replay-reference",
            }
        ],
    }
    payload = {
        **body,
        "artifact_digest": hashlib.sha256((_canonical(body) + "\n").encode("utf-8")).hexdigest(),
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_manifest_contains_state_identity_and_evidence_references(tmp_path: Path) -> None:
    commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, text=True).strip()
    artifact = _artifact(tmp_path / "closure.json", commit_sha)
    with patch("deployment.scripts.release_manifest._assert_clean_worktree"):
        manifest = build_manifest(repository_root=REPOSITORY_ROOT, artifact_paths=(artifact,))

    assert manifest["repository"]["branch"] == "main"
    assert "deployment/scripts/release_manifest.py" in manifest["tracked_files"]
    assert manifest["artifact_references"][0]["commit_sha"] == commit_sha
    assert manifest["artifact_references"][0]["immutable"] is True
    assert manifest["validation_evidence_references"] == [
        {
            "source": "enterprise_evidence_closure",
            "report_digest": "report-reference",
            "replay_digest": "replay-reference",
        }
    ]
    assert manifest["replay_digest_references"]
    assert "timestamps" in manifest["manifest_policy"]["identity_excludes"]


def test_manifest_verifies_artifact_provenance_and_rejects_mismatch(tmp_path: Path) -> None:
    commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, text=True).strip()
    artifact = _artifact(tmp_path / "closure.json", commit_sha)
    with patch("deployment.scripts.release_manifest._assert_clean_worktree"):
        manifest = build_manifest(repository_root=REPOSITORY_ROOT, artifact_paths=(artifact,))
    manifest_path = tmp_path / "release-manifest.json"
    with patch("deployment.scripts.release_manifest._assert_outside_repository"):
        write_manifest(manifest, output=manifest_path, repository_root=REPOSITORY_ROOT)

    with patch("deployment.scripts.release_manifest._assert_clean_worktree"), patch(
        "deployment.scripts.release_manifest._assert_outside_repository"
    ):
        verify_manifest(
            manifest_path=manifest_path,
            repository_root=REPOSITORY_ROOT,
            artifact_paths=(artifact,),
            require_artifact_references=True,
            require_validation_evidence=True,
        )

    tampered = json.loads(artifact.read_text(encoding="utf-8"))
    tampered["commit_sha"] = "0" * 40
    artifact.write_text(json.dumps(tampered), encoding="utf-8")
    with patch("deployment.scripts.release_manifest._assert_clean_worktree"), patch(
        "deployment.scripts.release_manifest._assert_outside_repository"
    ):
        with pytest.raises(ReleaseManifestError, match="commit association"):
            verify_manifest(
                manifest_path=manifest_path,
                repository_root=REPOSITORY_ROOT,
                artifact_paths=(artifact,),
                require_artifact_references=True,
            )

    _artifact(artifact, commit_sha)
    tampered_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tampered_manifest["replay_digest_references"][0]["digest"] = "tampered"
    tampered_manifest_path = tmp_path / "tampered-release-manifest.json"
    tampered_manifest_path.write_text(json.dumps(tampered_manifest), encoding="utf-8")
    with patch("deployment.scripts.release_manifest._assert_clean_worktree"), patch(
        "deployment.scripts.release_manifest._assert_outside_repository"
    ):
        with pytest.raises(ReleaseManifestError, match="replay digest references do not match"):
            verify_manifest(
                manifest_path=tampered_manifest_path,
                repository_root=REPOSITORY_ROOT,
                artifact_paths=(artifact,),
                require_artifact_references=True,
            )


def test_manifest_output_is_append_only(tmp_path: Path) -> None:
    with patch("deployment.scripts.release_manifest._assert_clean_worktree"):
        manifest = build_manifest(repository_root=REPOSITORY_ROOT)
    target = tmp_path / "release-manifest.json"
    with patch("deployment.scripts.release_manifest._assert_outside_repository"):
        write_manifest(manifest, output=target, repository_root=REPOSITORY_ROOT)
        with pytest.raises(ReleaseManifestError, match="refusing to overwrite"):
            write_manifest(manifest, output=target, repository_root=REPOSITORY_ROOT)


def test_release_hygiene_reports_bounded_repository_state() -> None:
    report = ReleaseHygieneValidator(
        repository_root=REPOSITORY_ROOT,
        generated_at="2026-08-25T00:00:00+00:00",
    ).run()

    state = report["evidence"]["repository_state"]
    assert report["validation_result"] == "blocked"
    assert state["tracked_modification_count"] >= 1
    assert state["untracked_release_impacting_count"] >= 1
    assert "RELEASE-HYGIENE:dirty_worktree" in report["blockers"]
