from __future__ import annotations

import base64
import json
import os
import stat
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "tools" / "sdna-custody"))

from sdna_custody.core import (  # noqa: E402
    CERTIFIED_ORIGIN,
    CustodyError,
    canonical_json,
    sha256_file,
    verify_manifest,
)
from sdna_custody.workflow import Authority  # noqa: E402


def bundle(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "bundle"
    (root / "node_modules" / "playwright").mkdir(parents=True, exist_ok=True)
    runtime = root / "approved-runtime.mjs"
    runtime.write_text("export async function setupBrowserRuntime() { return {}; }\n", encoding="utf-8")
    lockfile = root / "package-lock.json"
    lockfile.write_text(json.dumps({"packages": {"": {"dependencies": {"playwright": "1.0.0"}}, "node_modules/playwright": {"version": "1.0.0"}}}, sort_keys=True), encoding="utf-8")
    (root / "package.json").write_text(json.dumps({"private": True, "dependencies": {"playwright": "1.0.0"}}, sort_keys=True), encoding="utf-8")
    (root / "node_modules" / "playwright" / "package.json").write_text(json.dumps({"name": "playwright", "version": "1.0.0"}, sort_keys=True), encoding="utf-8")
    bridge = tmp_path / "bridge.mjs"
    bridge.write_text("export async function requestBrowserAuth() { return { status: 'submitted' }; }\n", encoding="utf-8")
    return runtime, lockfile, bridge


def authority(tmp_path: Path) -> Authority:
    auth = Authority(tmp_path / "state")
    auth.init_root("root-operator")
    auth.init_environment("staging", "root-operator")
    return auth


def request(auth: Authority, tmp_path: Path):
    runtime, lockfile, bridge = bundle(tmp_path)
    return auth.create_request(
        runtime=runtime,
        lockfile=lockfile,
        bridge=bridge,
        bridge_identity="sentinel-dna-browser-auth-bridge:1.0.0",
        image_digest="sha256:" + "a" * 64,
        image_reference="registry.example/sentinel-dna@sha256:" + "a" * 64,
        image_verification_reference="external-build:staging-001",
        origin=CERTIFIED_ORIGIN,
        requester="requester",
    )


def test_root_and_staging_key_initialization_and_listing(tmp_path):
    auth = authority(tmp_path)
    keys = auth.keys()
    assert len(keys) == 1
    assert keys[0]["environment"] == "staging"
    assert keys[0]["status"] == "ACTIVE"
    assert (tmp_path / "state" / "trust" / "root-private.pem").exists()
    if os.name != "nt":
        assert stat.S_IMODE((tmp_path / "state" / "trust" / "root-private.pem").stat().st_mode) == 0o600
    with pytest.raises(CustodyError, match="staging keys only"):
        auth.init_environment("production", "root-operator")


def test_artifact_hashes_and_deterministic_canonicalization(tmp_path):
    auth = authority(tmp_path)
    runtime, lockfile, bridge = bundle(tmp_path)
    assert sha256_file(runtime).startswith("sha256:")
    assert sha256_file(lockfile).startswith("sha256:")
    assert sha256_file(bridge).startswith("sha256:")
    assert canonical_json({"b": 1, "a": {"d": 2, "c": 3}}) == '{"a":{"c":3,"d":2},"b":1}'
    auth.close()


def test_signed_manifest_export_and_independent_verification(tmp_path):
    auth = authority(tmp_path)
    req = request(auth, tmp_path)
    manifest = auth.approve(req["approval_id"], "independent-reviewer")
    result = verify_manifest(manifest, auth.ledger, auth.signer)
    assert result["status"] == "PASS"
    output = tmp_path / "manifest.json"
    exported = auth.export_manifest(req["approval_id"], output)
    assert json.loads(output.read_text(encoding="utf-8")) == exported
    assert "PRIVATE" not in output.read_text(encoding="utf-8")


def test_invalid_signature_and_unknown_key_rejected(tmp_path):
    auth = authority(tmp_path)
    req = request(auth, tmp_path)
    manifest = auth.approve(req["approval_id"], "reviewer")
    manifest["signature"]["signature_b64"] = base64.b64encode(b"invalid").decode()
    with pytest.raises(CustodyError, match="signature"):
        verify_manifest(manifest, auth.ledger, auth.signer)
    manifest = json.loads(auth.ledger.one("SELECT manifest_json FROM approvals WHERE approval_id=?", (req["approval_id"],))["manifest_json"])
    manifest["signature"]["key_id"] = "unknown"
    with pytest.raises(CustodyError, match="unknown or revoked"):
        verify_manifest(manifest, auth.ledger, auth.signer)


def test_runtime_lockfile_and_bridge_tampering_rejected_before_approval(tmp_path):
    auth = authority(tmp_path)
    runtime, lockfile, bridge = bundle(tmp_path)
    req = auth.create_request(runtime=runtime, lockfile=lockfile, bridge=bridge, bridge_identity="bridge:1", image_digest="sha256:" + "b" * 64, image_reference="image", image_verification_reference="build:1", origin=CERTIFIED_ORIGIN, requester="requester")
    runtime.write_text("tampered", encoding="utf-8")
    with pytest.raises(CustodyError, match="changed"):
        auth.approve(req["approval_id"], "reviewer")
    lockfile.write_text("tampered", encoding="utf-8")
    with pytest.raises(CustodyError, match="changed"):
        auth.approve(req["approval_id"], "reviewer")
    bridge.write_text("tampered", encoding="utf-8")
    with pytest.raises(CustodyError, match="changed"):
        auth.approve(req["approval_id"], "reviewer")


def test_wrong_origin_and_missing_external_image_approval_rejected(tmp_path):
    auth = authority(tmp_path)
    runtime, lockfile, bridge = bundle(tmp_path)
    with pytest.raises(CustodyError, match="origin"):
        auth.create_request(runtime=runtime, lockfile=lockfile, bridge=bridge, bridge_identity="bridge:1", image_digest="sha256:" + "c" * 64, image_reference="image", image_verification_reference="build:1", origin="https://example.invalid", requester="requester")
    req = auth.create_request(runtime=runtime, lockfile=lockfile, bridge=bridge, bridge_identity="bridge:1", image_digest="sha256:" + "c" * 64, image_reference="image", image_verification_reference="", origin=CERTIFIED_ORIGIN, requester="requester")
    with pytest.raises(CustodyError, match="image"):
        auth.approve(req["approval_id"], "reviewer")


def test_separation_duplicate_and_expired_approval_rejection(tmp_path):
    auth = authority(tmp_path)
    req = request(auth, tmp_path)
    with pytest.raises(CustodyError, match="differ"):
        auth.approve(req["approval_id"], "requester")
    manifest = auth.approve(req["approval_id"], "reviewer", valid_days=-1)
    with pytest.raises(CustodyError, match="expired"):
        verify_manifest(manifest, auth.ledger, auth.signer)
    with pytest.raises(CustodyError, match="already exists"):
        auth.approve(req["approval_id"], "reviewer-two")


def test_revocation_and_key_lifecycle_fail_closed(tmp_path):
    auth = authority(tmp_path)
    req = request(auth, tmp_path)
    manifest = auth.approve(req["approval_id"], "reviewer")
    auth.revoke(req["approval_id"], "test revocation", "security-reviewer")
    with pytest.raises(CustodyError, match="revoked"):
        verify_manifest(manifest, auth.ledger, auth.signer)
    key_id = auth.keys()[0]["key_id"]
    auth.signer.set_key_status(key_id, "REVOKED", "security-reviewer", "key compromise test")
    assert auth.keys()[0]["status"] == "REVOKED"
    with pytest.raises(CustodyError):
        auth.signer.sign(b"payload")


def test_historical_rows_evidence_and_duplicate_exports_are_immutable(tmp_path):
    auth = authority(tmp_path)
    req = request(auth, tmp_path)
    auth.approve(req["approval_id"], "reviewer")
    evidence = auth.export_evidence(req["approval_id"], tmp_path / "evidence.json", "reviewer")
    assert evidence.exists()
    with pytest.raises(FileExistsError):
        auth.export_evidence(req["approval_id"], evidence, "reviewer")
    with pytest.raises(Exception):
        auth.ledger.db.execute("UPDATE approvals SET requester='attacker'")
    with pytest.raises(Exception):
        auth.ledger.db.execute("DELETE FROM audit_events")


def test_ledger_hash_chain_and_concurrent_requests(tmp_path):
    auth = authority(tmp_path)
    for _ in range(3):
        request(auth, tmp_path)
    events = auth.ledger.all("SELECT previous_hash,current_hash,event_json FROM audit_events ORDER BY rowid")
    previous = None
    for event in events:
        assert event["previous_hash"] == previous
        previous = event["current_hash"]

    def create_one(index):
        local = Authority(tmp_path / "state")
        try:
            runtime, lockfile, bridge = bundle(tmp_path / f"bundle-{index}")
            return local.create_request(runtime=runtime, lockfile=lockfile, bridge=bridge, bridge_identity=f"bridge:{index}", image_digest="sha256:" + "d" * 64, image_reference="image", image_verification_reference="build:1", origin=CERTIFIED_ORIGIN, requester=f"worker-{index}")["approval_id"]
        finally:
            local.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(create_one, (1, 2)))
    assert len(set(ids)) == 2
