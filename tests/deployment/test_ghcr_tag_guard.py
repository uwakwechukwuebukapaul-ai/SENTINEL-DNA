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
    return {"metadata": {"container": {"tags": list(tags)}}}


def test_candidate_tag_present_is_refused():
    assert ghcr_tag_guard.candidate_tag_exists(
        [_version("sha-deadbeef", "latest")], "sha-deadbeef"
    )


def test_candidate_tag_absent_after_complete_listing_is_distinguished():
    assert not ghcr_tag_guard.candidate_tag_exists(
        [_version("latest"), _version("sha-other")], "sha-target"
    )


def test_unknown_metadata_shapes_do_not_create_false_positive():
    assert not ghcr_tag_guard.candidate_tag_exists(
        [{"metadata": {}}, {"metadata": {"container": {"tags": "not-a-list"}}}],
        "sha-target",
    )


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
