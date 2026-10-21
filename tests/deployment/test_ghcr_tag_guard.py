from __future__ import annotations

import io
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from deployment.scripts import ghcr_tag_guard


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def _version(*tags: str) -> dict:
    return {
        "id": 123,
        "created_at": "2026-10-20T02:17:00Z",
        "metadata": {"container": {"tags": list(tags)}},
    }


def test_candidate_tag_present_is_refused():
    assert ghcr_tag_guard.candidate_tag_exists(
        [_version("sha-deadbeef", "latest")], "sha-deadbeef"
    )


def test_candidate_tag_absent_after_complete_listing_is_distinguished():
    assert not ghcr_tag_guard.candidate_tag_exists(
        [_version("latest"), _version("sha-other")], "sha-target"
    )


@pytest.mark.parametrize(
    "version",
    [
        {"id": 123, "created_at": "2026-10-20T02:17:00Z", "metadata": {}},
        {
            "id": 123,
            "created_at": "2026-10-20T02:17:00Z",
            "metadata": {"container": {"tags": "not-a-list"}},
        },
        {"id": 123, "metadata": {"container": {"tags": ["sha-target"]}}},
    ],
)
def test_incomplete_package_metadata_fails_closed(version):
    with pytest.raises(ghcr_tag_guard.ProbeError):
        ghcr_tag_guard.candidate_tag_exists([version], "sha-target")


def test_duplicate_tag_versions_fail_closed():
    with pytest.raises(ghcr_tag_guard.ProbeError, match="multiple package versions"):
        ghcr_tag_guard.candidate_tag_version([_version("sha-target"), _version("sha-target")], "sha-target")


def test_candidate_probe_reports_absent_and_present_without_authorizing_overwrite(tmp_path, monkeypatch, capsys):
    output = tmp_path / "github-output"
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-token")
    monkeypatch.setenv("GITHUB_API_URL", "https://api.github.com")
    monkeypatch.setattr(ghcr_tag_guard, "package_versions", lambda *_: [_version("latest")])
    monkeypatch.setattr("sys.argv", ["ghcr_tag_guard", "--image", "ghcr.io/example/image", "--tag", "sha-target", "--github-output", str(output)])

    assert ghcr_tag_guard.main() == 0
    assert "candidate_state=absent" in output.read_text()
    assert "absence confirmed" in capsys.readouterr().out

    output.write_text("")
    monkeypatch.setattr(ghcr_tag_guard, "package_versions", lambda *_: [_version("sha-target")])
    assert ghcr_tag_guard.main() == 0
    result = output.read_text()
    assert "candidate_state=present" in result
    assert "package_version_id=123" in result
    assert "package_created_at=2026-10-20T02:17:00Z" in result
    assert "recovery verification is required" in capsys.readouterr().out


def test_package_versions_paginates_until_a_short_page(monkeypatch):
    calls = []

    def fake_urlopen(request: Request, timeout: int):
        calls.append(request.full_url)
        page = int(request.full_url.rsplit("page=", 1)[1])
        if page == 1:
            return FakeResponse([_version(f"tag-{i}") for i in range(100)])
        return FakeResponse([_version("last-page-tag")])

    monkeypatch.setattr(ghcr_tag_guard, "urlopen", fake_urlopen)
    versions = ghcr_tag_guard.package_versions(
        "ghcr.io/example/sentinel-dna", "not-a-real-token", "https://api.github.com"
    )
    assert len(versions) == 101
    assert len(calls) == 2
    assert "page=1" in calls[0]
    assert "page=2" in calls[1]


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500])
def test_package_api_http_errors_are_inconclusive(monkeypatch, status):
    def fake_urlopen(request: Request, timeout: int):
        raise HTTPError(request.full_url, status, "failure", {}, io.BytesIO(b"secret body"))

    monkeypatch.setattr(ghcr_tag_guard, "urlopen", fake_urlopen)
    with pytest.raises(ghcr_tag_guard.ProbeError, match=f"HTTP {status}"):
        ghcr_tag_guard.package_versions(
            "ghcr.io/example/sentinel-dna", "not-a-real-token", "https://api.github.com"
        )


def test_network_error_is_inconclusive(monkeypatch):
    def fake_urlopen(request: Request, timeout: int):
        raise URLError("connection reset")

    monkeypatch.setattr(ghcr_tag_guard, "urlopen", fake_urlopen)
    with pytest.raises(ghcr_tag_guard.ProbeError, match="request failed"):
        ghcr_tag_guard.package_versions(
            "ghcr.io/example/sentinel-dna", "not-a-real-token", "https://api.github.com"
        )


def test_malformed_image_is_rejected_before_api_call():
    with pytest.raises(ghcr_tag_guard.ProbeError, match="image must be"):
        ghcr_tag_guard.package_versions("docker.io/example/image", "token", "https://api.github.com")
