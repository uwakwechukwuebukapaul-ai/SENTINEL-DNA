from __future__ import annotations

import pytest

from scripts.release_gate_diagnostics import (
    DEFAULT_BRANCH,
    DEFAULT_OWNER,
    DEFAULT_REPOSITORY,
    DEFAULT_REPOSITORY_ID,
    GitHubApiError,
    ReleaseGateDiagnostics,
    ReleaseGateError,
    RepositoryAddress,
    RepositoryResourceResolver,
    sanitize_error,
)


TARGET_SHA = "a3e349839625cedc879ffe021dcd084868b123cb"
OTHER_SHA = "b3e349839625cedc879ffe021dcd084868b123cb"


class FakeApi:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, resource):
        self.calls.append(resource)
        response = self.responses[resource]
        if isinstance(response, Exception):
            raise response
        return response


def run(
    database_id,
    workflow,
    *,
    sha=TARGET_SHA,
    status="completed",
    conclusion="success",
    event="push",
    branch=DEFAULT_BRANCH,
):
    return {
        "id": database_id,
        "name": workflow,
        "status": status,
        "conclusion": conclusion,
        "event": event,
        "head_sha": sha,
        "head_branch": branch,
    }


def repository():
    return RepositoryAddress(DEFAULT_OWNER, DEFAULT_REPOSITORY, DEFAULT_REPOSITORY_ID)


def diagnostic_api(*, runs, deployments=None, package_error=None):
    repo = repository()
    runs_resource = (
        "actions/runs?head_sha=" + TARGET_SHA + "&per_page=100"
    )
    deployment_resource = "deployments?sha=" + TARGET_SHA
    package_resource = "user/packages?package_type=container&per_page=100"
    return FakeApi(
        {
            repo.resource(runs_resource, numeric=True): {"workflow_runs": runs},
            repo.resource(deployment_resource, numeric=True): deployments or [],
            package_resource: package_error or [],
        }
    )


def make_diagnostic(api):
    return ReleaseGateDiagnostics(
        api,
        owner=DEFAULT_OWNER,
        repository=DEFAULT_REPOSITORY,
        repository_id=DEFAULT_REPOSITORY_ID,
        target_sha=TARGET_SHA,
    )


def test_owner_name_404_falls_back_to_authoritative_repository_id():
    repo = repository()
    canonical = repo.resource("actions/runs", numeric=False)
    numeric = repo.resource("actions/runs", numeric=True)
    api = FakeApi(
        {
            canonical: GitHubApiError(
                resource=canonical, status=404, reason="Not Found"
            ),
            numeric: {"workflow_runs": []},
        }
    )

    result = RepositoryResourceResolver(api, repo).get(
        "actions/runs", prefer_numeric=False
    )

    assert result == {"workflow_runs": []}
    assert api.calls == [canonical, numeric]


def test_diagnostics_use_numeric_repository_address_and_keep_ci_evidence_exact():
    api = diagnostic_api(
        runs=[
            run(32795099633, "security"),
            run(32795099621, "tests"),
            run(99999999999, "security", sha=OTHER_SHA),
        ]
    )

    result = make_diagnostic(api).collect()

    assert api.calls[0].startswith("repositories/1315476770/actions/runs?")
    assert not any(call.startswith("repos/") for call in api.calls)
    assert [item["databaseId"] for item in result.ci_runs] == [
        32795099633,
        32795099621,
    ]
    assert result.ci_status == "PASS"
    assert result.gate_status == "BLOCKED"


def test_unrelated_workflow_run_cannot_satisfy_exact_sha_gate():
    api = diagnostic_api(
        runs=[
            run(32795099633, "security"),
            run(32795099621, "tests", sha=OTHER_SHA),
        ]
    )

    with pytest.raises(ReleaseGateError, match="exact target SHA"):
        make_diagnostic(api).collect()


@pytest.mark.parametrize(
    ("status", "conclusion"),
    [("in_progress", None), ("completed", "failure")],
)
def test_failed_or_in_progress_runs_cannot_satisfy_gate(status, conclusion):
    api = diagnostic_api(
        runs=[
            run(32795099633, "security", status=status, conclusion=conclusion),
            run(32795099621, "tests"),
        ]
    )

    with pytest.raises(ReleaseGateError):
        make_diagnostic(api).collect()


def test_no_deployment_keeps_deployment_gate_blocked():
    api = diagnostic_api(
        runs=[run(32795099633, "security"), run(32795099621, "tests")],
        deployments=[],
    )

    result = make_diagnostic(api).collect()

    assert result.deployment_status == "BLOCKED"
    assert result.deployment_reason == "no deployment exists for the target SHA"


def test_missing_read_packages_permission_keeps_ghcr_absence_unproven():
    package_error = GitHubApiError(
        resource="user/packages?package_type=container&per_page=100",
        status=403,
        reason="You need at least read:packages scope to list packages",
    )
    api = diagnostic_api(
        runs=[run(32795099633, "security"), run(32795099621, "tests")],
        package_error=package_error,
    )

    result = make_diagnostic(api).collect()

    assert result.ghcr_status == "UNPROVEN"
    assert "read:packages" in result.ghcr_reason


def test_numeric_repository_failure_is_fail_closed_and_contextual():
    repo = repository()
    runs_resource = repo.resource(
        "actions/runs?head_sha=" + TARGET_SHA + "&per_page=100", numeric=True
    )
    api = FakeApi(
        {
            runs_resource: GitHubApiError(
                resource=runs_resource,
                status=404,
                reason="Not Found token=gho_super-secret-value",
            )
        }
    )

    with pytest.raises(ReleaseGateError) as raised:
        make_diagnostic(api).collect()

    message = str(raised.value)
    assert "repository_id=1315476770" in message
    assert "repository=uwakwechukwuebukpaul-ai/SENTINEL-DNA" in message
    assert f"target_sha={TARGET_SHA}" in message
    assert "repositories/1315476770/actions/runs" in message
    assert "http_status=404" in message
    assert "gho_super-secret-value" not in message
    assert "super-secret-value" not in message


def test_error_sanitization_removes_credentials_and_stderr_is_not_needed():
    raw = "Bearer gho_super-secret password=hunter2; secret=abc123"

    sanitized = sanitize_error(raw)

    assert "gho_super-secret" not in sanitized
    assert "hunter2" not in sanitized
    assert "abc123" not in sanitized
    assert "[redacted]" in sanitized
