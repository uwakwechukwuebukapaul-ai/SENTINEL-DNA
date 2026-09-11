from __future__ import annotations

import base64
import getpass
import hashlib
import json
import os
import re
import secrets
import sqlite3
import stat
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


SCHEMA_VERSION = "2.0"
ENVIRONMENT = "staging"
CERTIFIED_ORIGIN = "https://uwakwe-desktop.taile388cc.ts.net"
DOMAIN = b"SENTINEL-DNA-GATE5-MANIFEST-V2\n"
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$", re.IGNORECASE)
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{2,127}$")
STATUSES = {"ACTIVE", "GRACE", "REVOKED", "RETIRED"}


class CustodyError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CustodyError("CUSTODY_TIME_INVALID", "timestamp is invalid") from exc


def canonical_json(value: Any) -> str:
    """Canonical JSON v1: recursively sorted object keys, compact UTF-8 JSON."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    path = secure_file(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def secure_file(value: Path) -> Path:
    path = value.expanduser()
    if not path.is_absolute():
        path = path.absolute()
    try:
        if path.is_symlink():
            raise CustodyError("CUSTODY_SYMLINK_REJECTED", "symlink artifacts are rejected")
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise CustodyError("CUSTODY_ARTIFACT_MISSING", "artifact does not exist") from exc
    if not resolved.is_file():
        raise CustodyError("CUSTODY_ARTIFACT_INVALID", "artifact is not a regular file")
    return resolved


def validate_digest(value: str, field: str = "digest") -> str:
    if not isinstance(value, str) or not DIGEST_RE.fullmatch(value):
        raise CustodyError("CUSTODY_DIGEST_INVALID", f"{field} must be a sha256 digest")
    return value.lower()


def validate_identifier(value: str, field: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise CustodyError("CUSTODY_IDENTIFIER_INVALID", f"{field} is invalid")
    return value


def random_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(10)}"


def default_state_root() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Sentinel-DNA" / "custody"
    return Path("/var/lib/sentinel-dna/custody")


def _chmod_private(path: Path) -> None:
    if os.name != "nt":
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def _atomic_write(path: Path, data: bytes, mode: int = 0o600, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT
    flags |= os.O_EXCL if exclusive else os.O_TRUNC
    fd = os.open(path, flags, mode)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise
    _chmod_private(path)


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def database(self) -> Path:
        return self.root / "custody.db"

    @property
    def trust(self) -> Path:
        return self.root / "trust"

    @property
    def evidence(self) -> Path:
        return self.root / "evidence"

    @property
    def root_private(self) -> Path:
        return self.trust / "root-private.pem"

    @property
    def root_public(self) -> Path:
        return self.trust / "root-public.json"

    @property
    def staging_private(self) -> Path:
        return self.trust / "staging-private.pem"

    @property
    def staging_certificate(self) -> Path:
        return self.trust / "staging-certificate.json"


class Ledger:
    TABLES = (
        "trust_roots", "signing_keys", "operators", "approval_requests", "approvals",
        "artifact_bindings", "manifest_records", "evidence_records", "revocations",
        "key_lifecycle_events", "audit_events", "ledger_checkpoints",
    )

    def __init__(self, paths: Paths):
        self.paths = paths
        paths.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(paths.database, timeout=30, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA busy_timeout=30000")
        self._init_schema()

    def close(self) -> None:
        self.db.close()

    def _init_schema(self) -> None:
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS trust_roots (
              root_id TEXT PRIMARY KEY, environment TEXT NOT NULL UNIQUE,
              public_key_b64 TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE,
              created_at TEXT NOT NULL, status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS signing_keys (
              key_id TEXT PRIMARY KEY, environment TEXT NOT NULL,
              public_key_b64 TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE,
              created_at TEXT NOT NULL, valid_from TEXT NOT NULL,
              valid_until TEXT, status TEXT NOT NULL,
              certificate_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS key_lifecycle_events (
              event_id TEXT PRIMARY KEY, key_id TEXT NOT NULL, status TEXT NOT NULL,
              actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS operators (
              operator_id TEXT PRIMARY KEY, display_name TEXT NOT NULL,
              created_at TEXT NOT NULL, status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS approval_requests (
              approval_id TEXT PRIMARY KEY, approval_reference TEXT NOT NULL UNIQUE,
              environment TEXT NOT NULL, requester TEXT NOT NULL,
              request_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS approvals (
              approval_id TEXT PRIMARY KEY, approval_reference TEXT NOT NULL UNIQUE,
              environment TEXT NOT NULL, requester TEXT NOT NULL, approver TEXT NOT NULL,
              manifest_id TEXT NOT NULL UNIQUE, manifest_json TEXT NOT NULL,
              created_at TEXT NOT NULL, valid_until TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS artifact_bindings (
              approval_id TEXT NOT NULL, kind TEXT NOT NULL, identity TEXT NOT NULL,
              digest TEXT NOT NULL, verification TEXT NOT NULL, metadata_json TEXT NOT NULL,
              PRIMARY KEY (approval_id, kind), FOREIGN KEY (approval_id) REFERENCES approval_requests(approval_id)
            );
            CREATE TABLE IF NOT EXISTS manifest_records (
              manifest_id TEXT PRIMARY KEY, approval_id TEXT NOT NULL UNIQUE,
              manifest_hash TEXT NOT NULL UNIQUE, signature_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evidence_records (
              evidence_id TEXT PRIMARY KEY, approval_id TEXT NOT NULL,
              evidence_hash TEXT NOT NULL UNIQUE, path TEXT NOT NULL UNIQUE,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS revocations (
              revocation_id TEXT PRIMARY KEY, approval_id TEXT NOT NULL UNIQUE,
              reason TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_events (
              event_id TEXT PRIMARY KEY, approval_id TEXT, actor TEXT NOT NULL,
              environment TEXT NOT NULL, event_type TEXT NOT NULL,
              event_json TEXT NOT NULL, previous_hash TEXT, current_hash TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ledger_checkpoints (
              checkpoint_id TEXT PRIMARY KEY, last_event_id TEXT,
              ledger_hash TEXT NOT NULL, created_at TEXT NOT NULL
            );
            """
        )
        for table in self.TABLES:
            self.db.execute(
                f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_update "
                f"BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT, 'immutable custody record'); END;"
            )
            self.db.execute(
                f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_delete "
                f"BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT, 'immutable custody record'); END;"
            )

    def insert(self, table: str, values: dict[str, Any]) -> None:
        keys = list(values)
        placeholders = ",".join("?" for _ in keys)
        self.db.execute(
            f"INSERT INTO {table} ({','.join(keys)}) VALUES ({placeholders})",
            [values[key] for key in keys],
        )

    def one(self, query: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
        return self.db.execute(query, tuple(params)).fetchone()

    def all(self, query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        return self.db.execute(query, tuple(params)).fetchall()

    def audit(self, actor: str, environment: str, event_type: str, payload: dict[str, Any], approval_id: str | None = None) -> str:
        event_id = str(uuid.uuid4())
        created = utc_now()
        previous = self.one("SELECT current_hash FROM audit_events ORDER BY rowid DESC LIMIT 1")
        previous_hash = previous["current_hash"] if previous else None
        event = {
            "event_id": event_id, "actor": actor, "environment": environment,
            "event_type": event_type, "approval_id": approval_id,
            "payload": payload, "created_at": created,
        }
        current = sha256_bytes((previous_hash or "").encode() + canonical_json(event).encode())
        self.insert("audit_events", {
            "event_id": event_id, "approval_id": approval_id, "actor": actor,
            "environment": environment, "event_type": event_type,
            "event_json": canonical_json(event), "previous_hash": previous_hash,
            "current_hash": current, "created_at": created,
        })
        return event_id

    def checkpoint(self, actor: str, environment: str) -> str:
        last = self.one("SELECT event_id,current_hash FROM audit_events ORDER BY rowid DESC LIMIT 1")
        digest = last["current_hash"] if last else sha256_bytes(b"")
        checkpoint_id = str(uuid.uuid4())
        self.insert("ledger_checkpoints", {
            "checkpoint_id": checkpoint_id,
            "last_event_id": last["event_id"] if last else None,
            "ledger_hash": digest,
            "created_at": utc_now(),
        })
        self.audit(actor, environment, "LEDGER_CHECKPOINT", {"checkpoint_id": checkpoint_id, "ledger_hash": digest})
        return checkpoint_id


class LocalSigner:
    """Software signer behind the future KMS/HSM signer interface."""

    def __init__(self, paths: Paths, ledger: Ledger):
        self.paths = paths
        self.ledger = ledger

    @staticmethod
    def _private_bytes(key: Ed25519PrivateKey) -> bytes:
        return key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())

    @staticmethod
    def _public_b64(key: Ed25519PublicKey) -> str:
        return base64.b64encode(key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode("ascii")

    @staticmethod
    def _fingerprint(public_b64: str) -> str:
        return hashlib.sha256(base64.b64decode(public_b64)).hexdigest()

    def init_root(self, actor: str) -> dict[str, str]:
        if self.paths.root_private.exists():
            raise CustodyError("CUSTODY_ROOT_EXISTS", "root already exists")
        key = Ed25519PrivateKey.generate()
        public_b64 = self._public_b64(key.public_key())
        fingerprint = self._fingerprint(public_b64)
        _atomic_write(self.paths.root_private, self._private_bytes(key))
        _atomic_write(self.paths.root_public, (canonical_json({"root_id": "sdna-root-staging-bootstrap", "environment": ENVIRONMENT, "public_key_b64": public_b64, "fingerprint": fingerprint}) + "\n").encode(), 0o644)
        self.ledger.insert("trust_roots", {"root_id": "sdna-root-staging-bootstrap", "environment": ENVIRONMENT, "public_key_b64": public_b64, "fingerprint": fingerprint, "created_at": utc_now(), "status": "ACTIVE"})
        self.ledger.audit(actor, ENVIRONMENT, "ROOT_INITIALIZED", {"fingerprint": fingerprint})
        return {"root_id": "sdna-root-staging-bootstrap", "fingerprint": fingerprint}

    def init_environment(self, environment: str, actor: str) -> dict[str, str]:
        if environment != ENVIRONMENT:
            raise CustodyError("CUSTODY_ENVIRONMENT_REJECTED", "Phase 1 creates staging keys only")
        if not self.paths.root_private.exists():
            raise CustodyError("CUSTODY_ROOT_MISSING", "initialize the staging root first")
        if self.paths.staging_private.exists():
            raise CustodyError("CUSTODY_KEY_EXISTS", "staging key already exists")
        key = Ed25519PrivateKey.generate()
        public_b64 = self._public_b64(key.public_key())
        fingerprint = self._fingerprint(public_b64)
        root = serialization.load_pem_private_key(self.paths.root_private.read_bytes(), password=None)
        certificate = {"environment": environment, "key_id": "sdna-staging-" + fingerprint[:16], "public_key_b64": public_b64, "fingerprint": fingerprint, "valid_from": utc_now(), "valid_until": (datetime.now(timezone.utc) + timedelta(days=365)).replace(microsecond=0).isoformat().replace("+00:00", "Z")}
        certificate["signature_b64"] = base64.b64encode(root.sign(DOMAIN + canonical_json(certificate).encode())).decode("ascii")
        _atomic_write(self.paths.staging_private, self._private_bytes(key))
        _atomic_write(self.paths.staging_certificate, (canonical_json(certificate) + "\n").encode(), 0o644)
        self.ledger.insert("signing_keys", {"key_id": certificate["key_id"], "environment": environment, "public_key_b64": public_b64, "fingerprint": fingerprint, "created_at": utc_now(), "valid_from": certificate["valid_from"], "valid_until": certificate["valid_until"], "status": "ACTIVE", "certificate_json": canonical_json(certificate)})
        self.ledger.audit(actor, environment, "STAGING_KEY_INITIALIZED", {"key_id": certificate["key_id"], "fingerprint": fingerprint})
        return {"key_id": certificate["key_id"], "fingerprint": fingerprint}

    def list_keys(self) -> list[dict[str, Any]]:
        rows = self.ledger.all("SELECT key_id,environment,fingerprint,created_at,valid_from,valid_until,status FROM signing_keys ORDER BY created_at")
        result = []
        for row in rows:
            event = self.ledger.one("SELECT status FROM key_lifecycle_events WHERE key_id=? ORDER BY rowid DESC LIMIT 1", (row["key_id"],))
            item = dict(row)
            if event:
                item["status"] = event["status"]
            result.append(item)
        return result

    def set_key_status(self, key_id: str, status: str, actor: str, reason: str) -> dict[str, str]:
        if status not in STATUSES:
            raise CustodyError("CUSTODY_KEY_STATUS_INVALID", "unsupported key status")
        row = self.ledger.one("SELECT key_id,environment FROM signing_keys WHERE key_id=?", (key_id,))
        if not row:
            raise CustodyError("CUSTODY_KEY_UNKNOWN", "signing key is unknown")
        current = self.ledger.one("SELECT status FROM key_lifecycle_events WHERE key_id=? ORDER BY rowid DESC LIMIT 1", (key_id,))
        if current and current["status"] == "REVOKED":
            raise CustodyError("CUSTODY_KEY_REVOKED", "revoked keys cannot be reactivated")
        event = {"event_id": str(uuid.uuid4()), "key_id": key_id, "status": status, "actor": actor, "reason": reason, "created_at": utc_now()}
        self.ledger.insert("key_lifecycle_events", event)
        self.ledger.audit(actor, row["environment"], "SIGNING_KEY_STATUS_CHANGED", {"key_id": key_id, "status": status, "reason": reason})
        return event

    def _key_status(self, key_id: str) -> str | None:
        event = self.ledger.one("SELECT status FROM key_lifecycle_events WHERE key_id=? ORDER BY rowid DESC LIMIT 1", (key_id,))
        if event:
            return event["status"]
        row = self.ledger.one("SELECT status FROM signing_keys WHERE key_id=?", (key_id,))
        return row["status"] if row else None

    def _verify_certificate(self, certificate: dict[str, Any]) -> None:
        root_row = self.ledger.one("SELECT * FROM trust_roots WHERE environment=? AND status='ACTIVE'", (ENVIRONMENT,))
        if not root_row or certificate.get("environment") != ENVIRONMENT:
            raise CustodyError("CUSTODY_TRUST_ROOT_INVALID", "staging trust root is unavailable")
        signed = {key: value for key, value in certificate.items() if key != "signature_b64"}
        try:
            root = Ed25519PublicKey.from_public_bytes(base64.b64decode(root_row["public_key_b64"], validate=True))
            root.verify(base64.b64decode(certificate["signature_b64"], validate=True), DOMAIN + canonical_json(signed).encode())
        except Exception as exc:
            raise CustodyError("CUSTODY_TRUST_ROOT_INVALID", "staging key certificate is invalid") from exc

    def _load_staging(self) -> tuple[str, Ed25519PrivateKey, dict[str, Any]]:
        row = self.ledger.one("SELECT * FROM signing_keys WHERE environment=? ORDER BY created_at DESC LIMIT 1", (ENVIRONMENT,))
        if not row or self._key_status(row["key_id"]) not in {"ACTIVE", "GRACE"}:
            raise CustodyError("CUSTODY_SIGNING_KEY_UNAVAILABLE", "no usable staging signing key")
        key = serialization.load_pem_private_key(self.paths.staging_private.read_bytes(), password=None)
        certificate = json.loads(row["certificate_json"])
        self._verify_certificate(certificate)
        return row["key_id"], key, certificate

    def sign(self, payload: bytes, key_id: str | None = None) -> dict[str, str]:
        selected, key, _ = self._load_staging()
        if key_id and selected != key_id:
            raise CustodyError("CUSTODY_KEY_UNKNOWN", "requested key is not the active staging key")
        return {"algorithm": "Ed25519", "key_id": selected, "signature_b64": base64.b64encode(key.sign(DOMAIN + payload)).decode("ascii"), "domain": DOMAIN.decode().strip()}

    def verify(self, payload: bytes, signature: dict[str, Any]) -> bool:
        if signature.get("algorithm") != "Ed25519" or signature.get("domain") != DOMAIN.decode().strip():
            raise CustodyError("CUSTODY_SIGNATURE_INVALID", "signature algorithm or domain is invalid")
        row = self.ledger.one("SELECT * FROM signing_keys WHERE key_id=?", (signature.get("key_id"),))
        if not row or self._key_status(signature.get("key_id")) in {None, "REVOKED", "RETIRED"}:
            raise CustodyError("CUSTODY_KEY_REVOKED_OR_UNKNOWN", "signing key is unknown or revoked")
        self._verify_certificate(json.loads(row["certificate_json"]))
        certificate = json.loads(row["certificate_json"])
        if certificate.get("public_key_b64") != row["public_key_b64"] or certificate.get("fingerprint") != row["fingerprint"]:
            raise CustodyError("CUSTODY_KEY_CERTIFICATE_MISMATCH", "signing key certificate does not match the ledger")
        try:
            public = Ed25519PublicKey.from_public_bytes(base64.b64decode(row["public_key_b64"], validate=True))
            public.verify(base64.b64decode(signature["signature_b64"], validate=True), DOMAIN + payload)
        except Exception as exc:
            raise CustodyError("CUSTODY_SIGNATURE_INVALID", "signature verification failed") from exc
        return True


def dependency_closure_hash(bundle_root: Path) -> str:
    root = bundle_root.resolve(strict=True)
    files = [root / "package.json", root / "package-lock.json"]
    modules = root / "node_modules"
    if modules.exists():
        files.extend(sorted(modules.glob("*/package.json")))
    entries = []
    for file in files:
        if file.exists() and file.is_file() and not file.is_symlink():
            entries.append({"path": file.relative_to(root).as_posix(), "sha256": sha256_file(file)})
    if not entries:
        raise CustodyError("CUSTODY_CLOSURE_UNAVAILABLE", "dependency metadata is unavailable")
    return sha256_bytes(canonical_json({"algorithm": "metadata-v1", "entries": entries}).encode())


def artifact_bindings(runtime: Path, lockfile: Path, bridge: Path | None, image_digest: str, image_reference: str, image_verification_reference: str, origin: str) -> dict[str, dict[str, Any]]:
    if origin != CERTIFIED_ORIGIN:
        raise CustodyError("CUSTODY_ORIGIN_REJECTED", "only the certified staging origin is permitted")
    runtime = secure_file(runtime)
    lockfile = secure_file(lockfile)
    if bridge is not None:
        bridge = secure_file(bridge)
    bundle_root = runtime.parent
    return {
        "runtime": {"identity": "operator-approved:playwright-runtime:required", "digest": sha256_file(runtime), "verification": "LOCAL_BYTES", "source_path": str(runtime)},
        "lockfile": {"identity": str(lockfile), "digest": sha256_file(lockfile), "verification": "LOCAL_BYTES", "source_path": str(lockfile)},
        "dependency_closure": {"identity": "metadata-v1", "digest": dependency_closure_hash(bundle_root), "verification": "LOCAL_METADATA", "source_path": str(bundle_root)},
        "browser_auth_bridge": {"identity": str(bridge) if bridge else "NOT_SUPPLIED", "digest": sha256_file(bridge) if bridge else "NOT_SUPPLIED", "verification": "LOCAL_BYTES" if bridge else "REQUIRED", "source_path": str(bridge) if bridge else ""},
        "image": {"identity": image_reference, "digest": validate_digest(image_digest, "image_digest"), "verification": "EXTERNAL_REQUIRED", "verification_reference": image_verification_reference},
        "origin": {"identity": origin, "digest": sha256_bytes(origin.encode()), "verification": "POLICY_FIXED"},
    }


def manifest_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in manifest.items() if key not in {"integrity", "signature"}}


def make_manifest(request: dict[str, Any], bindings: dict[str, dict[str, Any]], signer: LocalSigner, valid_days: int = 30) -> dict[str, Any]:
    now = utc_now()
    key_id, _, _ = signer._load_staging()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "manifest_id": random_id("SDNA-MANIFEST"),
        "environment": ENVIRONMENT,
        "approval_reference": request["approval_reference"],
        "approval_status": "STAGING_LOCAL_APPROVED",
        "approved_at": now,
        "valid_until": (datetime.now(timezone.utc) + timedelta(days=valid_days)).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "issuer": {"identity": request["approver"], "role": "staging-custody-approver", "key_id": key_id},
        "provider": {"identity": "sentinel-dna:playwright-runtime-provider:1", "version": "1"},
        "runtime": {"identity": "operator-approved:playwright-runtime:required", "sha256": bindings["runtime"]["digest"]},
        "dependencies": {"lockfile_sha256": bindings["lockfile"]["digest"], "closure_sha256": bindings["dependency_closure"]["digest"], "closure_algorithm": "metadata-v1"},
        "image": {"identity": bindings["image"]["identity"], "sha256": bindings["image"]["digest"], "verification": bindings["image"]["verification"], "verification_reference": bindings["image"]["verification_reference"]},
        "browser_auth_bridge": {"identity": bindings["browser_auth_bridge"]["identity"], "sha256": bindings["browser_auth_bridge"]["digest"], "verification": bindings["browser_auth_bridge"]["verification"]},
        "certified_origin": CERTIFIED_ORIGIN,
        "policy_id": "gate5-staging-trusted-browser-v1",
        "evidence": [],
    }
    payload = canonical_json(manifest)
    manifest["integrity"] = {"algorithm": "sha256", "canonicalization": "sorted-json-v1", "manifest_hash": sha256_bytes(payload.encode())}
    manifest["signature"] = signer.sign(payload.encode())
    return manifest


def verify_manifest(manifest: dict[str, Any], ledger: Ledger, signer: LocalSigner, now: datetime | None = None) -> dict[str, Any]:
    required = {"schema_version", "manifest_id", "environment", "approval_reference", "approval_status", "approved_at", "valid_until", "issuer", "provider", "runtime", "dependencies", "image", "browser_auth_bridge", "certified_origin", "policy_id", "integrity", "signature"}
    if set(manifest) != required | {"evidence"}:
        raise CustodyError("CUSTODY_MANIFEST_INVALID", "manifest fields are incomplete or unexpected")
    if manifest["schema_version"] != SCHEMA_VERSION or manifest["environment"] != ENVIRONMENT:
        raise CustodyError("CUSTODY_MANIFEST_INVALID", "manifest schema or environment is invalid")
    if manifest["certified_origin"] != CERTIFIED_ORIGIN:
        raise CustodyError("CUSTODY_ORIGIN_REJECTED", "manifest origin is not certified")
    if manifest["approval_status"] != "STAGING_LOCAL_APPROVED":
        raise CustodyError("CUSTODY_APPROVAL_INVALID", "unsupported approval status")
    approval = ledger.one("SELECT approval_id,approval_reference,manifest_id FROM approvals WHERE manifest_id=?", (manifest["manifest_id"],))
    if not approval or approval["approval_reference"] != manifest["approval_reference"]:
        raise CustodyError("CUSTODY_APPROVAL_INVALID", "manifest is not bound to a ledger approval")
    calculated = sha256_bytes(canonical_json(manifest_payload(manifest)).encode())
    if manifest["integrity"].get("algorithm") != "sha256" or manifest["integrity"].get("canonicalization") != "sorted-json-v1" or manifest["integrity"].get("manifest_hash") != calculated:
        raise CustodyError("CUSTODY_INTEGRITY_INVALID", "manifest integrity does not match canonical payload")
    if parse_utc(manifest["valid_until"]) <= (now or datetime.now(timezone.utc)):
        raise CustodyError("CUSTODY_APPROVAL_EXPIRED", "manifest approval is expired")
    if ledger.one("SELECT 1 FROM revocations WHERE approval_id=(SELECT approval_id FROM approvals WHERE manifest_id=?)", (manifest["manifest_id"],)):
        raise CustodyError("CUSTODY_APPROVAL_REVOKED", "manifest approval is revoked")
    signer.verify(canonical_json(manifest_payload(manifest)).encode(), manifest["signature"])
    if manifest["issuer"].get("key_id") != manifest["signature"].get("key_id"):
        raise CustodyError("CUSTODY_SIGNATURE_INVALID", "issuer key and signature key differ")
    return {"status": "PASS", "manifest_id": manifest["manifest_id"], "manifest_hash": calculated}
