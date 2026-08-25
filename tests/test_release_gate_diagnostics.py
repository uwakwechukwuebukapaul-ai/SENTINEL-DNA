from __future__ import annotations

import pytest
from tests.credential_helpers import random_password, random_token

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
ACTUAL_TARGET_SHA = "e761308101af93ed8ea41a7eef9d2bb922540e89"


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
        "head_commit": {"id": sha},
        "repository": {
            "id": DEFAULT_REPOSITORY_ID,
            "full_name": f"{DEFAULT_OWNER}/{DEFAULT_REPOSITORY}",
        },
        "head_repository": {
            "id": DEFAULT_REPOSITORY_ID,
            "full_name": f"{DEFAULT_OWNER}/{DEFAULT_REPOSITORY}",
        },
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
            repo.resource(runs_resource, numeric=False): {"workflow_runs": runs},
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


def test_numeric_repository_id_can_resolve_owner_name_route():
    repo = repository()
    numeric = repo.resource("actions/runs", numeric=True)
    canonical = repo.resource("actions/runs", numeric=False)
    api = FakeApi(
        {
            numeric: GitHubApiError(
                resource=numeric, status=404, reason="Not Found"
            ),
            canonical: {"workflow_runs": []},
        }
    )

    result = RepositoryResourceResolver(api, repo).get(
        "actions/runs", prefer_numeric=True
    )

    assert result == {"workflow_runs": []}
    assert api.calls == [numeric, canonical]


def test_diagnostics_use_canonical_actions_route_and_keep_ci_evidence_exact():
    api = diagnostic_api(
        runs=[
            run(32795099633, "security"),
            run(32795099621, "tests"),
            run(99999999999, "security", sha=OTHER_SHA),
        ]
    )

    result = make_diagnostic(api).collect()

    assert api.calls[0].startswith(
        "repos/uwakwechukwuebukpaul-ai/SENTINEL-DNA/actions/runs?"
    )
    assert not any(
        call.startswith("repositories/1315476770/actions/runs?") for call in api.calls
    )
    assert [item["databaseId"] for item in result.ci_runs] == [
        32795099633,
        32795099621,
    ]
    assert result.ci_status == "PASS"
    assert result.gate_status == "BLOCKED"


def test_exact_github_actions_workflow_runs_payload_passes_all_ci_identity_checks():
    """The REST response uses nested head_repository custody metadata."""

    repo = repository()
    runs_resource = (
        "actions/runs?head_sha=" + ACTUAL_TARGET_SHA + "&per_page=100"
    )
    deployment_resource = "deployments?sha=" + ACTUAL_TARGET_SHA
    package_resource = "user/packages?package_type=container&per_page=100"
    run_payload = {
        "id": 32850238653,
        "name": "tests",
        "node_id": "MDg6V29ya2Zsb3dydW5pMzI4NTAyMzg2NTM=",
        "head_branch": "main",
        "head_sha": ACTUAL_TARGET_SHA,
        "run_number": 1,
        "event": "push",
        "status": "completed",
        "conclusion": "success",
        "workflow_id": 1,
        "head_commit": {"id": ACTUAL_TARGET_SHA},
        "repository": {
            "id": DEFAULT_REPOSITORY_ID,
            "full_name": f"{DEFAULT_OWNER}/{DEFAULT_REPOSITORY}",
        },
        "head_repository": {
            "id": DEFAULT_REPOSITORY_ID,
            "full_name": f"{DEFAULT_OWNER}/{DEFAULT_REPOSITORY}",
        },
    }
    api = FakeApi(
        {
            repo.resource(runs_resource, numeric=False): {
                "total_count": 1,
                "workflow_runs": [run_payload],
            },
            repo.resource(deployment_resource, numeric=True): [],
            package_resource: [],
        }
    )

    result = ReleaseGateDiagnostics(
        api,
        owner=DEFAULT_OWNER,
        repository=DEFAULT_REPOSITORY,
        repository_id=DEFAULT_REPOSITORY_ID,
        target_sha=ACTUAL_TARGET_SHA,
        expected_workflows=("tests",),
    ).collect()

    assert result.ci_status == "PASS"
    assert result.ci_runs[0]["databaseId"] == 32850238653
    assert result.ci_runs[0]["head_sha"] == ACTUAL_TARGET_SHA


def test_unrelated_workflow_run_cannot_satisfy_exact_sha_gate():
    api = diagnostic_api(
        runs=[
            run(32795099633, "security"),
            run(32795099621, "tests", sha=OTHER_SHA),
        ]
    )

    with pytest.raises(ReleaseGateError, match="exact target SHA"):
        make_diagnostic(api).collect()


def test_duplicate_exact_sha_runs_select_newest_run_deterministically():
    api = diagnostic_api(
        runs=[
            run(32795099633, "security"),
            run(32795099621, "tests"),
            run(32795100000, "security"),
        ]
    )

    result = make_diagnostic(api).collect()

    assert result.ci_runs[0]["databaseId"] == 32795100000
    assert result.custody_status == "PASS"


def test_run_from_different_repository_cannot_satisfy_custody_gate():
    api = diagnostic_api(
        runs=[run(32795099633, "security"), run(32795099621, "tests")]
    )
    repo = repository()
    resource = repo.resource(
        "actions/runs?head_sha=" + TARGET_SHA + "&per_page=100", numeric=False
    )
    api.responses[resource]["workflow_runs"][0]["repository"]["id"] = 999

    with pytest.raises(ReleaseGateError, match="repository ID"):
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


def test_unresolved_repository_identity_is_fail_closed_and_contextual():
    token = "gho_" + random_token()
    repo = repository()
    owner_resource = repo.resource(
        "actions/runs?head_sha=" + TARGET_SHA + "&per_page=100", numeric=False
    )
    api = FakeApi(
        {
            owner_resource: GitHubApiError(
                resource=owner_resource,
                status=404,
                reason=f"Not Found token={token}",
            ),
        }
    )

    with pytest.raises(ReleaseGateError) as raised:
        make_diagnostic(api).collect()

    message = str(raised.value)
    assert "repository_id=1315476770" in message
    assert "repository=uwakwechukwuebukpaul-ai/SENTINEL-DNA" in message
    assert f"target_sha={TARGET_SHA}" in message
    assert "repos/uwakwechukwuebukpaul-ai/SENTINEL-DNA/actions/runs" in message
    assert "http_status=404" in message
    assert token not in message
    assert token.removeprefix("gho_") not in message


def test_error_sanitization_removes_credentials_and_stderr_is_not_needed():
    token = "gho_" + random_token()
    password = random_password()
    secret = random_token()
    raw = f"Bearer {token} password={password}; secret={secret}"

    sanitized = sanitize_error(raw)

    assert token not in sanitized
    assert password not in sanitized
    assert secret not in sanitized
    assert "[redacted]" in sanitized
