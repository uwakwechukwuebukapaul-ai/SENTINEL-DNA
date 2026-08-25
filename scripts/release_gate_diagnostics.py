"""Read-only release-gate diagnostics for GitHub Actions evidence.

This module deliberately separates CI evidence from release authorization.  A
successful CI result never makes deployment, image custody, or GHCR publication
pass.  The numeric repository ID remains the authoritative custody identity,
while GitHub Actions resources are addressed through the canonical owner/name
route required by that API.
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


def _raise_blocked(
    *,
    repository: RepositoryAddress,
    target_sha: str,
    resource: str,
    status: int | None,
    check: str,
    expected: object,
    observed: object,
    reason: object,
) -> None:
    """Raise one bounded, structured fail-closed diagnostic error."""

    status_text = str(status) if status is not None else "unknown"
    expected_text = sanitize_error(expected) if expected is not None else "<none>"
    observed_text = sanitize_error(observed) if observed is not None else "<missing>"
    raise ReleaseGateError(
        "release-gate diagnostics blocked: "
        f"repository_id={repository.repository_id}; "
        f"repository={repository.canonical}; "
        f"target_sha={target_sha}; "
        f"requested_api_resource={sanitize_error(resource)}; "
        f"http_status={status_text}; "
        f"check={sanitize_error(check)}; "
        f"expected={expected_text}; "
        f"observed={observed_text}; "
        f"reason={sanitize_error(reason)}"
    )


class RepositoryResourceResolver:
    """Resolve a repository resource with explicit numeric-ID preference.

    ``prefer_numeric=True`` first tries the numeric repository route, then
    falls back to the owner/name route on HTTP 404.  ``prefer_numeric=False``
    preserves the inverse order for callers that already use an owner/name
    route.  No non-404 error is hidden by either mode.  Callers for APIs that
    require canonical owner/name addressing must use the canonical route
    directly rather than relying on numeric fallback.
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


@dataclass(frozen=True)
class WorkflowRunsResponse:
    """Normalized response envelope returned by an Actions runs provider."""

    total_count: Any
    runs: tuple["NormalizedWorkflowRun", ...]
    api_resource: str


@dataclass(frozen=True)
class NormalizedWorkflowRun:
    """Provider-neutral workflow-run evidence normalized from GitHub JSON."""

    database_id: Any
    workflow_id: Any
    workflow_name: Any
    run_number: Any
    status: Any
    conclusion: Any
    event: Any
    head_branch: Any
    head_sha: Any
    head_commit_id: Any
    repository_id: Any
    repository_full_name: Any
    head_repository_id: Any
    head_repository_full_name: Any
    timestamp: str | None
    api_resource: str
    payload_format: str

    def as_evidence(
        self,
        *,
        validation_result: str,
        failure_reason: str | None = None,
    ) -> dict[str, Any]:
        """Preserve normalized evidence without retaining unbounded raw JSON."""

        return {
            "databaseId": self.database_id,
            "workflowId": self.workflow_id,
            "workflow": self.workflow_name,
            "runNumber": self.run_number,
            "status": self.status,
            "conclusion": self.conclusion,
            "event": self.event,
            "head_branch": self.head_branch,
            "head_sha": self.head_sha,
            "repository": {
                "id": self.repository_id,
                "full_name": self.repository_full_name,
            },
            "head_repository": {
                "id": self.head_repository_id,
                "full_name": self.head_repository_full_name,
            },
            "repository_identity": {
                "repository_id": self.repository_id,
                "repository_full_name": self.repository_full_name,
                "head_repository_id": self.head_repository_id,
                "head_repository_full_name": self.head_repository_full_name,
            },
            "api_resource": self.api_resource,
            "timestamp": self.timestamp,
            "validation_result": validation_result,
            "failure_reason": failure_reason,
            "payload_format": self.payload_format,
        }


class GitHubActionsProvider:
    """Fetch, normalize, and validate GitHub Actions workflow evidence.

    Release-gate business logic consumes ``NormalizedWorkflowRun`` objects and
    does not depend on GitHub's nested response layout.  The legacy
    ``head_repository_id`` shape is accepted only when the repository ID and
    repository full name independently establish the expected custody
    identity; a partial or conflicting nested shape remains blocked.
    """

    def __init__(
        self,
        api: GitHubApi,
        repository: RepositoryAddress,
        *,
        target_sha: str,
        expected_branch: str | None,
        expected_event: str,
    ):
        self.api = api
        self.repository = repository
        self.target_sha = target_sha
        self.expected_branch = expected_branch
        self.expected_event = expected_event

    def fetch_runs(self) -> WorkflowRunsResponse:
        resource = "actions/runs?" + urlencode(
            {"head_sha": self.target_sha, "per_page": 100}
        )
        resource = self.repository.resource(resource, numeric=False)
        try:
            payload = self.api.get(resource)
        except GitHubApiError as exc:
            self._blocked(
                resource,
                exc.status,
                check="actions_api_response",
                expected="HTTP 200 JSON with workflow_runs list",
                observed=f"HTTP {exc.status if exc.status is not None else 'unknown'}: {exc.reason}",
                reason="Actions workflow-runs request failed",
            )

        if not isinstance(payload, Mapping):
            self._blocked(
                resource,
                None,
                check="actions_api_response",
                expected="JSON object with workflow_runs list",
                observed=type(payload).__name__,
                reason="Actions response envelope is invalid",
            )
        workflow_runs = payload.get("workflow_runs")
        if not isinstance(workflow_runs, list):
            self._blocked(
                resource,
                None,
                check="workflow_runs_parsing",
                expected="workflow_runs=list",
                observed=type(workflow_runs).__name__,
                reason="Actions response field is missing or invalid",
            )
        if not all(isinstance(run, Mapping) for run in workflow_runs):
            self._blocked(
                resource,
                None,
                check="workflow_runs_parsing",
                expected="every workflow_runs entry is an object",
                observed="one or more non-object entries",
                reason="Actions response contains invalid run entries",
            )
        return WorkflowRunsResponse(
            total_count=payload.get("total_count"),
            runs=tuple(self.normalize_run(run, resource=resource) for run in workflow_runs),
            api_resource=resource,
        )

    def normalize_run(
        self, run: Mapping[str, Any], *, resource: str
    ) -> NormalizedWorkflowRun:
        """Normalize nested and legacy identity fields without validating them."""

        repository = run.get("repository")
        repository_id = repository.get("id") if isinstance(repository, Mapping) else None
        repository_full_name = (
            repository.get("full_name") if isinstance(repository, Mapping) else None
        )
        head_repository = run.get("head_repository")
        if isinstance(head_repository, Mapping):
            head_repository_id = head_repository.get("id")
            head_repository_full_name = head_repository.get("full_name")
            payload_format = "nested"
        else:
            head_repository_id = run.get("head_repository_id")
            head_repository_full_name = None
            payload_format = "legacy"
        head_commit = run.get("head_commit")
        timestamp = next(
            (
                run.get(field)
                for field in ("updated_at", "created_at", "run_started_at")
                if isinstance(run.get(field), str) and run.get(field)
            ),
            None,
        )
        return NormalizedWorkflowRun(
            database_id=run.get("id"),
            workflow_id=run.get("workflow_id"),
            workflow_name=run.get("name"),
            run_number=run.get("run_number"),
            status=run.get("status"),
            conclusion=run.get("conclusion"),
            event=run.get("event"),
            head_branch=run.get("head_branch"),
            head_sha=run.get("head_sha"),
            head_commit_id=(
                head_commit.get("id") if isinstance(head_commit, Mapping) else None
            ),
            repository_id=repository_id,
            repository_full_name=repository_full_name,
            head_repository_id=head_repository_id,
            head_repository_full_name=head_repository_full_name,
            timestamp=timestamp,
            api_resource=resource,
            payload_format=payload_format,
        )

    def validate_identity(
        self, run: NormalizedWorkflowRun, workflow: str
    ) -> None:
        """Require every custody, identity, and successful-run invariant."""

        if run.head_sha != self.target_sha or run.head_commit_id != self.target_sha:
            self._blocked(
                run.api_resource,
                None,
                check="target_sha",
                expected=f"head_sha={self.target_sha}; head_commit.id={self.target_sha}",
                observed=(
                    f"head_sha={run.head_sha!r}; "
                    f"head_commit.id={run.head_commit_id!r}"
                ),
                reason="workflow run is not bound to the exact target SHA",
            )
        if run.workflow_name != workflow:
            self._blocked(
                run.api_resource,
                None,
                check="workflow_identity",
                expected=workflow,
                observed=f"name={run.workflow_name!r}; workflow_id={run.workflow_id!r}",
                reason="workflow identity validation failed",
            )
        if run.status != "completed":
            self._blocked(
                run.api_resource,
                None,
                check="workflow_status",
                expected="completed",
                observed=run.status,
                reason="workflow run is not completed",
            )
        if run.conclusion != "success":
            self._blocked(
                run.api_resource,
                None,
                check="workflow_conclusion",
                expected="success",
                observed=run.conclusion,
                reason="workflow run did not conclude successfully",
            )
        if run.event != self.expected_event:
            self._blocked(
                run.api_resource,
                None,
                check="workflow_event",
                expected=self.expected_event,
                observed=run.event,
                reason="workflow event validation failed",
            )
        if self.expected_branch is not None and run.head_branch != self.expected_branch:
            self._blocked(
                run.api_resource,
                None,
                check="workflow_branch",
                expected=self.expected_branch,
                observed=run.head_branch,
                reason="workflow branch validation failed",
            )
        identity_observed = (
            f"repository.id={run.repository_id!r}; "
            f"repository.full_name={run.repository_full_name!r}; "
            f"head_repository.id={run.head_repository_id!r}; "
            f"head_repository.full_name={run.head_repository_full_name!r}"
        )
        if (
            run.repository_id != self.repository.repository_id
            or run.repository_full_name != self.repository.canonical
            or run.head_repository_id != self.repository.repository_id
            or (
                run.payload_format == "nested"
                and run.head_repository_full_name != self.repository.canonical
            )
        ):
            self._blocked(
                run.api_resource,
                None,
                check="repository_identity",
                expected=(
                    f"repository.id={self.repository.repository_id}; "
                    f"repository.full_name={self.repository.canonical}; "
                    f"head_repository.id={self.repository.repository_id}; "
                    f"head_repository.full_name={self.repository.canonical}"
                ),
                observed=identity_observed,
                reason="custody validation failed: repository ID or name mismatch",
            )
        if not isinstance(run.database_id, int) or isinstance(run.database_id, bool) or run.database_id <= 0:
            self._blocked(
                run.api_resource,
                None,
                check="workflow_database_id",
                expected="positive integer",
                observed=run.database_id,
                reason="workflow run database ID is invalid",
            )

    def _blocked(
        self,
        resource: str,
        status: int | None,
        *,
        check: str,
        expected: object,
        observed: object,
        reason: object,
    ) -> None:
        _raise_blocked(
            repository=self.repository,
            target_sha=self.target_sha,
            resource=resource,
            status=status,
            check=check,
            expected=expected,
            observed=observed,
            reason=reason,
        )


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
        self.actions = GitHubActionsProvider(
            api,
            self.repository,
            target_sha=target_sha,
            expected_branch=expected_branch,
            expected_event=expected_event,
        )

    def collect(self) -> ReleaseGateResult:
        runs_response = self.actions.fetch_runs()
        exact_runs = [
            run for run in runs_response.runs if run.head_sha == self.target_sha
        ]

        evidence: list[Mapping[str, Any]] = []
        for workflow in self.expected_workflows:
            matches = [run for run in exact_runs if run.workflow_name == workflow]
            if not matches:
                self._blocked(
                    runs_response.api_resource,
                    None,
                    check="workflow_runs_matching",
                    expected=f"workflow={workflow}; head_sha={self.target_sha}",
                    observed=(
                        f"matching_runs={len(matches)}; "
                        f"available_workflows={sorted({run.workflow_name for run in exact_runs if isinstance(run.workflow_name, str)})}"
                    ),
                    reason=f"no {workflow} run was found for the exact target SHA",
                )
            run = self._select_deterministic_run(
                matches,
                workflow,
                runs_response.api_resource,
            )
            self.actions.validate_identity(run, workflow)
            evidence.append(run.as_evidence(validation_result="PASS"))

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
                check="deployment_response",
                expected="JSON list",
                observed=type(deployments).__name__,
                reason="deployment API returned an unexpected payload",
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
        matches: list[NormalizedWorkflowRun],
        workflow: str,
        resource: str,
    ) -> NormalizedWorkflowRun:
        """Select the newest exact-SHA run without hiding an invalid winner.

        A commit can legitimately produce more than one push run (for example,
        when a tag is created after the branch push).  Run IDs are monotonic in
        GitHub's Actions API, so the largest valid integer ID is a stable
        tie-breaker.  The selected run still has to pass every custody and
        success check below; an older failed run is evidence, not a reason to
        let a newer successful run become ambiguous.
        """

        if not all(
            isinstance(run.database_id, int)
            and not isinstance(run.database_id, bool)
            and run.database_id > 0
            for run in matches
        ):
            self._blocked(
                resource,
                None,
                check="workflow_database_id",
                expected=f"{workflow} run has a positive integer database ID",
                observed=[run.database_id for run in matches],
                reason=f"{workflow} run database ID is invalid",
            )
        return max(matches, key=lambda run: run.database_id)

    def _authoritative_get(self, suffix: str):
        try:
            return self.resources.get(suffix, prefer_numeric=True)
        except GitHubApiError as exc:
            self._blocked(
                exc.resource,
                exc.status,
                check="authoritative_api_response",
                expected="successful JSON response",
                observed=f"HTTP {exc.status if exc.status is not None else 'unknown'}: {exc.reason}",
                reason="authoritative repository API request failed",
            )

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

    def _blocked(
        self,
        resource: str,
        status: int | None,
        *,
        check: str,
        expected: object,
        observed: object,
        reason: object,
    ) -> None:
        _raise_blocked(
            repository=self.repository,
            target_sha=self.target_sha,
            resource=resource,
            status=status,
            check=check,
            expected=expected,
            observed=observed,
            reason=reason,
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
