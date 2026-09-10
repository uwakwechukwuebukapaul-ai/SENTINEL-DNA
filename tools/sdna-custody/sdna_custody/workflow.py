from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .core import (
    CERTIFIED_ORIGIN,
    ENVIRONMENT,
    CustodyError,
    Ledger,
    LocalSigner,
    Paths,
    _atomic_write,
    artifact_bindings,
    canonical_json,
    make_manifest,
    random_id,
    sha256_bytes,
    sha256_file,
    dependency_closure_hash,
    secure_file,
    utc_now,
    verify_manifest,
)


def actor(explicit: str | None) -> str:
    value = explicit or os.environ.get("SDNA_CUSTODY_OPERATOR_ID") or os.environ.get("USERNAME") or os.environ.get("USER")
    if not value:
        raise CustodyError("CUSTODY_ACTOR_REQUIRED", "provide --actor or SDNA_CUSTODY_OPERATOR_ID")
    return value


class Authority:
    def __init__(self, state_root: Path):
        self.paths = Paths(state_root.expanduser().absolute())
        self.ledger = Ledger(self.paths)
        self.signer = LocalSigner(self.paths, self.ledger)

    def close(self) -> None:
        self.ledger.close()

    def _ensure_operator(self, operator_id: str) -> None:
        if not self.ledger.one("SELECT 1 FROM operators WHERE operator_id=?", (operator_id,)):
            self.ledger.insert("operators", {"operator_id": operator_id, "display_name": operator_id, "created_at": utc_now(), "status": "ACTIVE"})

    def init_root(self, actor_id: str) -> dict[str, Any]:
        self._ensure_operator(actor_id)
        return self.signer.init_root(actor_id)

    def init_environment(self, environment: str, actor_id: str) -> dict[str, Any]:
        self._ensure_operator(actor_id)
        return self.signer.init_environment(environment, actor_id)

    def keys(self) -> list[dict[str, Any]]:
        return self.signer.list_keys()

    def create_request(self, *, runtime: Path, lockfile: Path, bridge: Path | None, bridge_identity: str, image_digest: str, image_reference: str, image_verification_reference: str, origin: str, requester: str) -> dict[str, Any]:
        self._ensure_operator(requester)
        if bridge is None:
            raise CustodyError("CUSTODY_BRIDGE_REQUIRED", "browser-auth bridge is required for a Gate 5 artifact request")
        approval_id = random_id("SDNA-REQUEST")
        reference = random_id("SDNA-STG")
        bindings = artifact_bindings(runtime, lockfile, bridge, image_digest, image_reference, image_verification_reference, origin)
        bindings["browser_auth_bridge"]["identity"] = bridge_identity
        request = {
            "approval_id": approval_id,
            "approval_reference": reference,
            "environment": ENVIRONMENT,
            "requester": requester,
            "runtime": bindings["runtime"],
            "dependencies": {"lockfile": bindings["lockfile"], "closure": bindings["dependency_closure"]},
            "browser_auth_bridge": bindings["browser_auth_bridge"],
            "image": bindings["image"],
            "origin": bindings["origin"],
            "created_at": utc_now(),
        }
        self.ledger.insert("approval_requests", {"approval_id": approval_id, "approval_reference": reference, "environment": ENVIRONMENT, "requester": requester, "request_json": canonical_json(request), "created_at": request["created_at"]})
        for kind, binding in bindings.items():
            self.ledger.insert("artifact_bindings", {"approval_id": approval_id, "kind": kind, "identity": str(binding["identity"]), "digest": str(binding["digest"]), "verification": str(binding["verification"]), "metadata_json": canonical_json(binding)})
        self.ledger.audit(requester, ENVIRONMENT, "APPROVAL_REQUEST_CREATED", {"approval_reference": reference, "artifact_digests": {k: v["digest"] for k, v in bindings.items()}}, approval_id)
        return request

    def approve(self, approval_id: str, approver: str, valid_days: int = 30) -> dict[str, Any]:
        if self.ledger.one("SELECT 1 FROM approvals WHERE approval_id=?", (approval_id,)):
            raise CustodyError("CUSTODY_DUPLICATE_APPROVAL", "approval already exists")
        row = self.ledger.one("SELECT * FROM approval_requests WHERE approval_id=?", (approval_id,))
        if not row:
            raise CustodyError("CUSTODY_REQUEST_NOT_FOUND", "approval request not found")
        request = json.loads(row["request_json"])
        self._ensure_operator(approver)
        if request["requester"] == approver:
            raise CustodyError("CUSTODY_SEPARATION_REQUIRED", "requester and approver must differ")
        bindings = {r["kind"]: json.loads(r["metadata_json"]) for r in self.ledger.all("SELECT * FROM artifact_bindings WHERE approval_id=?", (approval_id,))}
        for kind in ("runtime", "lockfile", "browser_auth_bridge"):
            current = bindings[kind]
            if sha256_file(secure_file(Path(current["source_path"]))) != current["digest"]:
                raise CustodyError("CUSTODY_ARTIFACT_CHANGED", f"{kind} changed after request creation")
        closure = dependency_closure_hash(Path(bindings["dependency_closure"]["source_path"]))
        if closure != bindings["dependency_closure"]["digest"]:
            raise CustodyError("CUSTODY_ARTIFACT_CHANGED", "dependency closure changed after request creation")
        if bindings["image"]["verification"] != "EXTERNAL_REQUIRED" or not bindings["image"].get("verification_reference"):
            raise CustodyError("CUSTODY_IMAGE_APPROVAL_REQUIRED", "image requires an external verification reference")
        request["approver"] = approver
        manifest = make_manifest(request, bindings, self.signer, valid_days)
        manifest_hash = manifest["integrity"]["manifest_hash"]
        self.ledger.insert("approvals", {"approval_id": approval_id, "approval_reference": request["approval_reference"], "environment": ENVIRONMENT, "requester": request["requester"], "approver": approver, "manifest_id": manifest["manifest_id"], "manifest_json": canonical_json(manifest), "created_at": manifest["approved_at"], "valid_until": manifest["valid_until"]})
        self.ledger.insert("manifest_records", {"manifest_id": manifest["manifest_id"], "approval_id": approval_id, "manifest_hash": manifest_hash, "signature_json": canonical_json(manifest["signature"]), "created_at": manifest["approved_at"]})
        self.ledger.audit(approver, ENVIRONMENT, "APPROVAL_SIGNED", {"approval_reference": request["approval_reference"], "manifest_id": manifest["manifest_id"], "manifest_hash": manifest_hash}, approval_id)
        self.ledger.checkpoint(approver, ENVIRONMENT)
        return manifest

    def export_manifest(self, approval_id: str, output: Path) -> dict[str, Any]:
        row = self.ledger.one("SELECT manifest_json FROM approvals WHERE approval_id=?", (approval_id,))
        if not row:
            raise CustodyError("CUSTODY_APPROVAL_NOT_FOUND", "approved manifest not found")
        manifest = json.loads(row["manifest_json"])
        _atomic_write(output, (canonical_json(manifest) + "\n").encode(), 0o644, exclusive=True)
        self.ledger.audit(actor(None), ENVIRONMENT, "MANIFEST_EXPORTED", {"manifest_id": manifest["manifest_id"], "manifest_hash": manifest["integrity"]["manifest_hash"]}, approval_id)
        return manifest

    def revoke(self, approval_id: str, reason: str, actor_id: str) -> dict[str, Any]:
        row = self.ledger.one("SELECT approval_reference FROM approvals WHERE approval_id=?", (approval_id,))
        if not row:
            raise CustodyError("CUSTODY_APPROVAL_NOT_FOUND", "approval not found")
        if self.ledger.one("SELECT 1 FROM revocations WHERE approval_id=?", (approval_id,)):
            raise CustodyError("CUSTODY_ALREADY_REVOKED", "approval already revoked")
        self._ensure_operator(actor_id)
        record = {"revocation_id": random_id("SDNA-REVOCATION"), "approval_id": approval_id, "reason": reason, "actor": actor_id, "created_at": utc_now()}
        self.ledger.insert("revocations", record)
        self.ledger.audit(actor_id, ENVIRONMENT, "APPROVAL_REVOKED", {"approval_reference": row["approval_reference"], "reason": reason}, approval_id)
        self.ledger.checkpoint(actor_id, ENVIRONMENT)
        return record

    def export_evidence(self, approval_id: str, output: Path | None, actor_id: str) -> Path:
        row = self.ledger.one("SELECT * FROM approvals WHERE approval_id=?", (approval_id,))
        if not row:
            raise CustodyError("CUSTODY_APPROVAL_NOT_FOUND", "approval not found")
        manifest = json.loads(row["manifest_json"])
        audit = [dict(r) for r in self.ledger.all("SELECT event_id,actor,event_type,event_json,previous_hash,current_hash,created_at FROM audit_events WHERE approval_id=? ORDER BY rowid", (approval_id,))]
        checkpoint = self.ledger.one("SELECT * FROM ledger_checkpoints ORDER BY rowid DESC LIMIT 1")
        evidence = {"schema_version": "1.0", "evidence_id": random_id("SDNA-EVIDENCE"), "approval_reference": row["approval_reference"], "approval_request": json.loads(self.ledger.one("SELECT request_json FROM approval_requests WHERE approval_id=?", (approval_id,))["request_json"]), "manifest": manifest, "verification": verify_manifest(manifest, self.ledger, self.signer), "audit_references": audit, "ledger_checkpoint": dict(checkpoint) if checkpoint else None, "generated_at": utc_now()}
        evidence["evidence_hash"] = sha256_bytes(canonical_json(evidence).encode())
        destination = output or (self.paths.evidence / f"{evidence['evidence_id']}.json")
        _atomic_write(destination, (canonical_json(evidence) + "\n").encode(), 0o644, exclusive=True)
        self.ledger.insert("evidence_records", {"evidence_id": evidence["evidence_id"], "approval_id": approval_id, "evidence_hash": evidence["evidence_hash"], "path": str(destination), "created_at": evidence["generated_at"]})
        self.ledger.audit(actor_id, ENVIRONMENT, "EVIDENCE_EXPORTED", {"evidence_id": evidence["evidence_id"], "evidence_hash": evidence["evidence_hash"]}, approval_id)
        return destination

    def export_audit(self, approval_id: str, output: Path, actor_id: str) -> Path:
        events = [dict(row) for row in self.ledger.all("SELECT * FROM audit_events WHERE approval_id=? ORDER BY rowid", (approval_id,))]
        if not events:
            raise CustodyError("CUSTODY_AUDIT_NOT_FOUND", "approval audit not found")
        payload = {"schema_version": "1.0", "approval_id": approval_id, "events": events, "exported_at": utc_now()}
        _atomic_write(output, (canonical_json(payload) + "\n").encode(), 0o644, exclusive=True)
        self.ledger.audit(actor_id, ENVIRONMENT, "AUDIT_EXPORTED", {"approval_id": approval_id}, approval_id)
        return output
