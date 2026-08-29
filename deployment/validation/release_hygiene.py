"""Evidence-only release hygiene and manifest validation."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Iterable

from deployment.scripts.release_manifest import ReleaseManifestError, build_manifest, repository_branch, verify_manifest


REPORT_VERSION = "sentinel-dna-release-hygiene-validation.v1"
REPLAY_VERSION = "sentinel-dna-release-hygiene-replay.v1"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any) -> str:
    return hashlib.sha256((_canonical(value) + "\n").encode("utf-8")).hexdigest()


class ReleaseHygieneValidator:
    """Validate release-boundary evidence without changing repository state."""

    def __init__(
        self,
        *,
        repository_root: str | Path,
        manifest_path: str | Path | None = None,
        artifact_paths: Iterable[str | Path] = (),
        expected_branch: str | None = None,
        generated_at: str | None = None,
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.manifest_path = Path(manifest_path).resolve() if manifest_path else None
        self.artifact_paths = tuple(Path(path).resolve() for path in artifact_paths)
        self.expected_branch = expected_branch
        self.generated_at = str(generated_at or datetime.now(timezone.utc).isoformat())

    def _git(self, *args: str) -> str:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.repository_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        return result.stdout.strip()

    def _repository_state(self) -> dict[str, Any]:
        status = self._git("status", "--porcelain=v1", "--untracked-files=all")
        ignored = self._git("status", "--porcelain=v1", "--ignored", "--untracked-files=all")
        tracked: list[dict[str, str]] = []
        untracked: list[dict[str, str]] = []
        ignored_files: list[dict[str, str]] = []
        for line in status.splitlines():
            if len(line) < 4:
                continue
            code, path = line[:2], line[3:]
            item = {"status": code, "path": path.replace("\\", "/")}
            if code == "??":
                untracked.append(item)
            elif code != "!!":
                tracked.append(item)
        for line in ignored.splitlines():
            if len(line) >= 4 and line[:2] == "!!":
                ignored_files.append({"status": "!!", "path": line[3:].replace("\\", "/")})

        def is_transient(path: str) -> bool:
            return (
                path.startswith(("work/", ".pytest_cache/"))
                or path.endswith((".pyc", ".tmp", ".temp"))
                or "/__pycache__/" in f"/{path}/"
                or path.endswith("/__pycache__")
            )

        untracked_release_impacting = [item for item in untracked if not is_transient(item["path"])]
        accidental_temporary = [item for item in untracked if is_transient(item["path"])]
        ignored_temporary = [item for item in ignored_files if is_transient(item["path"])]
        generated_artifacts = [
            item for item in untracked_release_impacting
            if item["path"].startswith(("artifacts/", "release-evidence/"))
        ]
        release_impacting = tracked + untracked_release_impacting

        def sample(items: list[dict[str, str]]) -> list[dict[str, str]]:
            return sorted(items, key=lambda item: (item["path"], item["status"]))[:100]

        return {
            "tracked_modification_count": len(tracked),
            "tracked_modifications": sample(tracked),
            "untracked_file_count": len(untracked),
            "untracked_files": sample(untracked),
            "untracked_release_impacting_count": len(untracked_release_impacting),
            "untracked_release_impacting_files": sample(untracked_release_impacting),
            "ignored_file_count": len(ignored_files),
            "ignored_files": sample(ignored_files),
            "generated_artifact_count": len(generated_artifacts),
            "generated_artifacts": sample(generated_artifacts),
            "accidental_temporary_file_count": len(accidental_temporary),
            "accidental_temporary_files": sample(accidental_temporary),
            "ignored_temporary_file_count": len(ignored_temporary),
            "ignored_temporary_files": sample(ignored_temporary),
            "release_impacting_change_count": len(release_impacting),
            "release_impacting_changes": sample(release_impacting),
        }

    @staticmethod
    def _artifact_is_valid(path: Path, commit_sha: str) -> bool:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
            return False
        if not isinstance(payload, dict):
            return False
        if payload.get("immutable") is not True:
            return False
        if payload.get("commit_sha") != commit_sha:
            return False
        if not payload.get("artifact_digest") or not payload.get("replay_digest"):
            return False
        stored_artifact_digest = payload["artifact_digest"]
        artifact_body = dict(payload)
        artifact_body.pop("artifact_digest", None)
        if _digest(artifact_body) != stored_artifact_digest:
            return False
        references = payload.get("replay_digest_references")
        if not isinstance(references, list) or not references or any(
            not isinstance(item, dict) or not item.get("source") or not item.get("digest")
            for item in references
        ):
            return False
        if not ReleaseHygieneValidator._closure_replay_is_consistent(payload):
            return False
        return True

    @staticmethod
    def _closure_replay_is_consistent(payload: dict[str, Any]) -> bool:
        if not all(key in payload for key in ("evidence_sources", "control_matrix", "passed_controls", "pending_controls", "failed_controls", "remaining_blockers")):
            return False
        references = payload.get("replay_digest_references", ())
        source_names = [item.get("source") for item in references if isinstance(item, dict)]
        sources = sorted(
            [
                {
                "source": item.get("source"),
                "status": item.get("status"),
                "replay_digest": item.get("replay_digest"),
                }
            for item in payload["evidence_sources"]
            if isinstance(item, dict)
            ],
            key=lambda item: (str(item["source"]), str(item["replay_digest"])),
        )
        stable = {
            "replay_version": "sentinel-dna-enterprise-evidence-closure-replay.v1",
            "source_names": source_names,
            "sources": sources,
            "controls": payload["control_matrix"],
            "passed_controls": payload["passed_controls"],
            "pending_controls": payload["pending_controls"],
            "failed_controls": payload["failed_controls"],
            "blockers": payload["remaining_blockers"],
        }
        return _digest(stable) == payload.get("replay_digest")

    def run(self) -> dict[str, Any]:
        commit_sha = self._git("rev-parse", "HEAD")
        branch = repository_branch(self.repository_root)
        repository_state = self._repository_state()
        clean = bool(commit_sha) and not repository_state["tracked_modifications"] and not repository_state["untracked_release_impacting_files"]
        branch_ok = bool(branch) and (self.expected_branch is None or branch == self.expected_branch)
        manifest_error: str | None = None
        manifest_verified = False
        manifest_generated = False
        try:
            if self.manifest_path is not None:
                verify_manifest(
                    manifest_path=self.manifest_path,
                    repository_root=self.repository_root,
                    require_current_head=True,
                    artifact_paths=self.artifact_paths,
                    require_artifact_references=bool(self.artifact_paths),
                    require_validation_evidence=bool(self.artifact_paths),
                )
                manifest_verified = True
                manifest_generated = True
            elif commit_sha:
                build_manifest(
                    repository_root=self.repository_root,
                    release_sha=commit_sha,
                    artifact_paths=self.artifact_paths,
                )
                manifest_generated = True
                manifest_verified = True
            else:
                manifest_error = "commit_sha_unavailable"
        except ReleaseManifestError as exc:
            manifest_error = type(exc).__name__

        artifact_results = {
            str(path): self._artifact_is_valid(path, commit_sha)
            for path in self.artifact_paths
        }
        artifact_provenance = bool(artifact_results) and all(artifact_results.values())
        immutable_references = artifact_provenance
        checks = {
            "clean_git_worktree": clean,
            "no_unexpected_tracked_modifications": not repository_state["tracked_modifications"],
            "no_untracked_release_impacting_files": not repository_state["untracked_release_impacting_files"],
            "release_branch_state": branch_ok,
            "release_manifest_generated": manifest_generated,
            "release_manifest_verified": manifest_verified,
            "manifest_matches_repository_state": manifest_verified,
            "artifact_provenance_present": artifact_provenance,
            "immutable_evidence_references": immutable_references,
            "commit_sha_captured": bool(commit_sha),
        }
        blockers: list[str] = []
        if not clean:
            blockers.append("RELEASE-HYGIENE:dirty_worktree")
        if repository_state["tracked_modifications"]:
            blockers.append("RELEASE-HYGIENE:unexpected_tracked_modifications")
        if repository_state["untracked_release_impacting_files"]:
            blockers.append("RELEASE-HYGIENE:untracked_release_impacting_files")
        if not branch_ok:
            blockers.append("RELEASE-HYGIENE:release_branch_state")
        if not manifest_generated:
            blockers.append(f"RELEASE-HYGIENE:manifest_generation:{manifest_error or 'not_generated'}")
        if not manifest_verified:
            blockers.append(f"RELEASE-HYGIENE:manifest_verification:{manifest_error or 'not_verified'}")
            blockers.append("RELEASE-HYGIENE:manifest_matches_repository_state")
        if not artifact_provenance:
            blockers.append("RELEASE-HYGIENE:artifact_provenance_missing_or_invalid")
        if not commit_sha:
            blockers.append("RELEASE-HYGIENE:commit_sha_missing")
        evidence_missing = not manifest_generated or not manifest_verified or not artifact_provenance
        result = "passed" if all(checks.values()) else ("blocked" if evidence_missing else "failed")
        evidence = {
            "commit_sha": commit_sha or None,
            "branch": branch or None,
            "status_observed": bool(repository_state["release_impacting_change_count"] or repository_state["ignored_file_count"]),
            "repository_state": repository_state,
            "manifest_path_supplied": self.manifest_path is not None,
            "artifact_paths": [str(path) for path in self.artifact_paths],
            "artifact_validity": sorted(artifact_results.values()),
            "artifact_count": len(artifact_results),
            "secrets_serialized": False,
            "production_mutation_performed": False,
        }
        stable = {
            "replay_version": REPLAY_VERSION,
            "checks": checks,
            "blockers": sorted(set(blockers)),
            "commit_sha": commit_sha,
            "branch": branch,
            "artifact_results": artifact_results,
        }
        replay = _digest(stable)
        body = {
            "report_version": REPORT_VERSION,
            "generated_at": self.generated_at,
            "validation_result": result,
            "checks": checks,
            "blockers": sorted(set(blockers)),
            "warnings": [
                "release_hygiene_is_observation_only_and_does_not_authorize_deployment",
                "release_hygiene_does_not_print_or_serialize_secrets",
                "ignored_files_are_reported_but_not_treated_as_release_changes",
            ],
            "evidence": evidence,
            "replay_digest": replay,
        }
        return {**body, "report_digest": _digest(body)}


__all__ = ["ReleaseHygieneValidator"]
