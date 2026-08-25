"""Read-only release-gate diagnostics for GitHub Actions evidence.

This module deliberately separates CI evidence from release authorization.  A
successful CI result never makes deployment, image custody, or GHCR publication
pass.  GitHub Actions resources are addressed by the authoritative numeric
repository ID because the owner/name route can return HTTP 404 for this
repository.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Mapping, Protocol
from urllib.parse import urlencode


DEFAULT_OWNER = "uwakwechukwuebukpaul-ai"
DEFAULT_REPOSITORY = "SENTINEL-DNA"
DEFAULT_REPOSITORY_ID = 1315476770
DEFAULT_BRANCH: str | None = None
DEFAULT_WORKFLOWS = ("security", "tests")

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_HTTP_STATUS_RE = re.compile(r"\bHTTP\s+(\d{3})\b", re.IGNORECASE)
_TOKEN_RE = re.compile(
    r"(?i)(?:gh[pousr]_|github_pat_|x-access-token:|bearer\s+)[A-Za-z0-9._-]+"
)
_KEY_VALUE_SECRET_RE = re.compile(
    r"(?i)\b(token|password|secret|authorization|credential)\s*[:=]\s*[^\s,;]+"
)


def sanitize_error(value: object) -> str:
    """Return a bounded error reason without credentials or command noise."""

    text = str(value)
    text = _TOKEN_RE.sub("[redacted]", text)
    text = _KEY_VALUE_SECRET_RE.sub(r"\1=[redacted]", text)
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text[:240] or "GitHub API request failed"


class GitHubApiError(RuntimeError):
    """Safe representation of a failed GitHub API request."""

    def __init__(self, *, resource: str, status: int | None, reason: object):
        self.resource = sanitize_error(resource)
        self.status = status
        self.reason = sanitize_error(reason)
        status_text = str(status) if status is not None else "unknown"
        super().__init__(
            "GitHub API request failed: "
            f"resource={self.resource}; http_status={status_text}; reason={self.reason}"
        )


class ReleaseGateError(RuntimeError):
    """Fail-closed diagnostic error safe to print to an operator."""


class GitHubApi(Protocol):
    def get(self, resource: str) -> Mapping[str, Any] | list[Any]: ...


class GhApiClient:
    """Minimal read-only adapter around ``gh api``.

    The subprocess stderr is intentionally never included in an exception.
    GitHub's JSON error message is used when available and sanitized before it
    reaches a caller.
    """

    def get(self, resource: str) -> Mapping[str, Any] | list[Any]:
        try:
            completed = subprocess.run(
                ["gh", "api", resource],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        except OSError as exc:
            raise GitHubApiError(
                resource=resource,
                status=None,
                reason="GitHub CLI unavailable",
            ) from exc

        if completed.returncode != 0:
            status = _status_from_output(completed.stdout, completed.stderr)
            reason = _reason_from_json(completed.stdout) or "GitHub API request failed"
            raise GitHubApiError(resource=resource, status=status, reason=reason)

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise GitHubApiError(
                resource=resource,
                status=None,
                reason="GitHub API returned invalid JSON",
            ) from exc
        if not isinstance(payload, (dict, list)):
            raise GitHubApiError(
                resource=resource,
                status=None,
                reason="GitHub API returned an unexpected payload",
            )
        return payload


def _status_from_output(stdout: str, stderr: str) -> int | None:
    match = _HTTP_STATUS_RE.search(f"{stdout}\n{stderr}")
    return int(match.group(1)) if match else None


def _reason_from_json(output: str) -> str | None:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict) and payload.get("message"):
        return sanitize_error(payload["message"])
    return None


@dataclass(frozen=True)
class RepositoryAddress:
    owner: str
    name: str
    repository_id: int

    @property
    def canonical(self) -> str:
        return f"{self.owner}/{self.name}"

    def resource(self, suffix: str, *, numeric: bool) -> str:
        prefix = (
            f"repositories/{self.repository_id}"
            if numeric
            else f"repos/{self.owner}/{self.name}"
        )
        return f"{prefix}/{suffix.lstrip('/')}"


class RepositoryResourceResolver:
    """Resolve a repository resource with explicit numeric-ID preference.

    ``prefer_numeric=True`` first tries the numeric repository route, then
    falls back to the owner/name route when GitHub does not expose that
    resource by numeric ID.  GitHub's Actions and deployment endpoints use
    owner/name routes even when the numeric repository ID is the authoritative
    custody identity.  ``prefer_numeric=False`` preserves the inverse order
    for callers that already use an owner/name route.  No non-404 error is
    hidden by either mode.
    """

    def __init__(self, api: GitHubApi, repository: RepositoryAddress):
        self.api = api
        self.repository = repository

    def get(self, suffix: str, *, prefer_numeric: bool = True):
        routes = (
            ((True, False), (False, True))
            if prefer_numeric
            else ((False, False), (True, True))
        )
        last_error: GitHubApiError | None = None
        for numeric, _ in routes:
            resource = self.repository.resource(suffix, numeric=numeric)
            try:
                return self.api.get(resource)
            except GitHubApiError as exc:
                last_error = exc
                if exc.status != 404:
                    raise
        assert last_error is not None
        raise last_error


@dataclass(frozen=True)
class ReleaseGateResult:
    repository: str
    repository_id: int
    target_sha: str
    ci_status: str
    ci_runs: tuple[Mapping[str, Any], ...]
    custody_status: str
    custody_reason: str
    deployment_status: str
    deployment_reason: str
    ghcr_status: str
    ghcr_reason: str
    gate_status: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "repository": self.repository,
            "repository_id": self.repository_id,
            "target_sha": self.target_sha,
            "ci": {"status": self.ci_status, "runs": list(self.ci_runs)},
            "commit_custody": {
                "status": self.custody_status,
                "reason": self.custody_reason,
            },
            "deployment": {
                "status": self.deployment_status,
                "reason": self.deployment_reason,
            },
            "ghcr": {"status": self.ghcr_status, "reason": self.ghcr_reason},
            "gate_status": self.gate_status,
        }


class ReleaseGateDiagnostics:
    """Collect non-authorizing CI, deployment, and GHCR evidence."""

    def __init__(
        self,
        api: GitHubApi,
        *,
        owner: str = DEFAULT_OWNER,
        repository: str = DEFAULT_REPOSITORY,
        repository_id: int = DEFAULT_REPOSITORY_ID,
        target_sha: str,
        expected_branch: str | None = DEFAULT_BRANCH,
        expected_workflows: tuple[str, ...] = DEFAULT_WORKFLOWS,
        expected_event: str = "push",
    ):
        if not _SHA_RE.fullmatch(target_sha):
            raise ValueError("target_sha must be a 40-character lowercase Git SHA")
        if repository_id <= 0:
            raise ValueError("repository_id must be positive")
        if not expected_workflows:
            raise ValueError("expected_workflows must not be empty")
        self.api = api
        self.repository = RepositoryAddress(owner, repository, repository_id)
        self.target_sha = target_sha
        self.expected_branch = expected_branch
        self.expected_workflows = expected_workflows
        self.expected_event = expected_event
        self.resources = RepositoryResourceResolver(api, self.repository)

    def collect(self) -> ReleaseGateResult:
        runs_resource = "actions/runs?" + urlencode(
            {"head_sha": self.target_sha, "per_page": 100}
        )
        runs_payload = self._authoritative_get(runs_resource)
        runs = self._list_field(runs_payload, "workflow_runs", runs_resource)
        exact_runs = [run for run in runs if run.get("head_sha") == self.target_sha]

        evidence: list[Mapping[str, Any]] = []
        for workflow in self.expected_workflows:
            matches = [run for run in exact_runs if run.get("name") == workflow]
            if not matches:
                self._blocked(
                    self.repository.resource(runs_resource, numeric=True),
                    None,
                    f"no {workflow} run was found for the exact target SHA",
                )
            run = self._select_deterministic_run(
                matches,
                workflow,
                self.repository.resource(runs_resource, numeric=True),
            )
            self._require_run_identity(
                run,
                workflow,
                self.repository.resource(runs_resource, numeric=True),
            )
            evidence.append(
                {
                    "databaseId": run.get("id"),
                    "workflow": run.get("name"),
                    "runNumber": run.get("run_number"),
                    "status": run.get("status"),
                    "conclusion": run.get("conclusion"),
                    "event": run.get("event"),
                    "head_branch": run.get("head_branch"),
                    "head_sha": run.get("head_sha"),
                }
            )

        custody_reason = (
            "selected workflow runs are bound to the exact target SHA and "
            "authoritative repository identity"
        )

        deployments_resource = "deployments?" + urlencode({"sha": self.target_sha})
        deployments = self._authoritative_get(deployments_resource)
        if not isinstance(deployments, list):
            self._blocked(
                deployments_resource,
                None,
                "deployment API returned an unexpected payload",
            )
        if deployments:
            deployment_reason = (
                "deployment records exist, but deployment authorization remains separate"
            )
        else:
            deployment_reason = "no deployment exists for the target SHA"

        ghcr_status, ghcr_reason = self._ghcr_status()
        return ReleaseGateResult(
            repository=self.repository.canonical,
            repository_id=self.repository.repository_id,
            target_sha=self.target_sha,
            ci_status="PASS",
            ci_runs=tuple(evidence),
            custody_status="PASS",
            custody_reason=custody_reason,
            deployment_status="BLOCKED",
            deployment_reason=deployment_reason,
            ghcr_status=ghcr_status,
            ghcr_reason=ghcr_reason,
            gate_status="BLOCKED",
        )

    def _select_deterministic_run(
        self,
        matches: list[Mapping[str, Any]],
        workflow: str,
        resource: str,
    ) -> Mapping[str, Any]:
        """Select the newest exact-SHA run without hiding an invalid winner.

        A commit can legitimately produce more than one push run (for example,
        when a tag is created after the branch push).  Run IDs are monotonic in
        GitHub's Actions API, so the largest valid integer ID is a stable
        tie-breaker.  The selected run still has to pass every custody and
        success check below; an older failed run is evidence, not a reason to
        let a newer successful run become ambiguous.
        """

        if not all(isinstance(run.get("id"), int) and run["id"] > 0 for run in matches):
            self._blocked(resource, None, f"{workflow} run database ID is invalid")
        return max(matches, key=lambda run: run["id"])

    def _authoritative_get(self, suffix: str):
        try:
            return self.resources.get(suffix, prefer_numeric=True)
        except GitHubApiError as exc:
            self._blocked(exc.resource, exc.status, exc.reason)

    def _list_field(
        self, payload: Mapping[str, Any] | list[Any], field: str, resource: str
    ) -> list[Mapping[str, Any]]:
        if not isinstance(payload, Mapping) or not isinstance(payload.get(field), list):
            self._blocked(resource, None, f"response field {field} is missing or invalid")
        values = payload[field]
        if not all(isinstance(value, Mapping) for value in values):
            self._blocked(resource, None, f"response field {field} contains invalid entries")
        return list(values)

    def _require_run_identity(
        self, run: Mapping[str, Any], workflow: str, resource: str
    ) -> None:
        if run.get("head_sha") != self.target_sha:
            self._blocked(resource, None, f"{workflow} run SHA does not match target SHA")
        if run.get("name") != workflow:
            self._blocked(resource, None, f"workflow identity mismatch for {workflow}")
        if run.get("status") != "completed":
            self._blocked(resource, None, f"{workflow} run is not completed")
        if run.get("conclusion") != "success":
            self._blocked(resource, None, f"{workflow} run conclusion is not success")
        if run.get("event") != self.expected_event:
            self._blocked(
                resource,
                None,
                f"{workflow} run event {run.get('event')!r} is not {self.expected_event!r}",
            )
        if self.expected_branch is not None and run.get("head_branch") != self.expected_branch:
            self._blocked(
                resource,
                None,
                f"{workflow} run branch does not match expected branch",
            )
        if not isinstance(run.get("id"), int) or run["id"] <= 0:
            self._blocked(resource, None, f"{workflow} run database ID is invalid")
        repository = run.get("repository")
        if not isinstance(repository, Mapping):
            self._blocked(resource, None, f"{workflow} repository custody payload is invalid")
        if repository.get("id") != self.repository.repository_id:
            self._blocked(resource, None, f"{workflow} run repository ID does not match custody")
        if repository.get("full_name") != self.repository.canonical:
            self._blocked(resource, None, f"{workflow} run repository name does not match custody")
        head_repository_id = run.get("head_repository_id")
        if head_repository_id != self.repository.repository_id:
            self._blocked(resource, None, f"{workflow} head repository ID does not match custody")
        head_commit = run.get("head_commit")
        if not isinstance(head_commit, Mapping) or head_commit.get("id") != self.target_sha:
            self._blocked(resource, None, f"{workflow} head commit does not match custody")

    def _ghcr_status(self) -> tuple[str, str]:
        resource = "user/packages?" + urlencode(
            {"package_type": "container", "per_page": 100}
        )
        try:
            self.api.get(resource)
        except GitHubApiError as exc:
            if exc.status == 403:
                return (
                    "UNPROVEN",
                    "container package inventory unavailable; token lacks read:packages",
                )
            return "UNPROVEN", f"container package inventory unavailable: {exc.reason}"
        return (
            "UNPROVEN",
            "package inventory was readable, but candidate image custody was not established",
        )

    def _blocked(self, resource: str, status: int | None, reason: object):
        status_text = str(status) if status is not None else "unknown"
        raise ReleaseGateError(
            "release-gate diagnostics blocked: "
            f"repository_id={self.repository.repository_id}; "
            f"repository={self.repository.canonical}; "
            f"target_sha={self.target_sha}; "
            f"requested_api_resource={sanitize_error(resource)}; "
            f"http_status={status_text}; reason={sanitize_error(reason)}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--repository-id", type=int, default=DEFAULT_REPOSITORY_ID)
    parser.add_argument("--target-sha", required=True)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    diagnostics = ReleaseGateDiagnostics(
        GhApiClient(),
        owner=args.owner,
        repository=args.repository,
        repository_id=args.repository_id,
        target_sha=args.target_sha,
        expected_branch=args.branch,
    )
    try:
        result = diagnostics.collect()
    except (GitHubApiError, ReleaseGateError) as exc:
        print(sanitize_error(exc), file=sys.stderr)
        return 2
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0 if result.gate_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
