"""Fail-closed Gate4 signed release-manifest boundary.

This module deliberately separates cryptographic signature validation from signer
trust validation. Production signature and status providers are injected; the
default providers fail closed because production trust infrastructure is not
part of this repository change.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
import re
import secrets
import subprocess
import struct
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

SCHEMA_VERSION = "gate4.release-manifest.v1"
ACTIVATION_PATH = "deployment/staging/scripts/trusted_browser_activation_manifest.mjs"
ACTIVATION_VALIDATOR_PATH = ACTIVATION_PATH
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
FORBIDDEN_KEY_RE = re.compile(r"(?:secret|password|credential|private[_-]?key|token)", re.I)
MUTABLE_IMAGE_RE = re.compile(r"(?:^|/)[^/@\s]+:[^/@\s]+$")
ARRAY_SORT_KEYS = {
    "artifacts.sentinel_built_images": "identity",
    "artifacts.external_boundary_images": "identity",
    "artifacts.third_party_images": "identity",
    "artifacts.provenance": "identity",
}


class ManifestError(ValueError):
    pass


class SignatureValidator(Protocol):
    def verify(self, payload: bytes, envelope: dict[str, Any]) -> "SignatureResult": ...


class StatusProvider(Protocol):
    def status(self, manifest_digest: str, signer_identity: str, candidate: dict[str, Any] | None = None) -> "StatusResult": ...


class EvidenceVerifier(Protocol):
    """Independently authenticates evidence returned by an external adapter."""

    def verify(self, evidence: dict[str, Any], subject_digest: str) -> None: ...


class ReplayAuthority(Protocol):
    """Externally durable, authenticated, atomic nonce-consumption authority."""

    def consume(self, *, authority_identity: str, provider_identity: str, operation: str, request_id: str, nonce: bytes, request_hash: str, subject_digest: str, candidate_tuple_digest: str) -> "ReplayDecision": ...


class EvidenceRetriever(Protocol):
    """External authenticated retrieval of immutable evidence bytes."""

    def retrieve(self, reference: str) -> "EvidenceBytes": ...


class RevocationAuthority(Protocol):
    def verify(self, response: dict[str, Any]) -> bool: ...


class TransparencyAuthority(Protocol):
    def verify(self, response: dict[str, Any]) -> bool: ...


class IdentityAuthority(Protocol):
    def verify(self, claims: dict[str, Any]) -> dict[str, str]: ...


class TrustRootAuthority(Protocol):
    def verify(self, reference: str, digest: str, root: dict[str, Any]) -> "AuthorityAttestation": ...


@dataclass(frozen=True)
class SignatureResult:
    valid: bool
    signer_identity: str
    issuer: str
    transparency_reference: str
    verification_reference: str = ""
    verified_at: str = ""
    revocation_status: str = ""
    verification_method_identity: str = ""
    verification_method_version: str = ""


@dataclass(frozen=True)
class StatusResult:
    status: str
    authority_reference: str = ""
    checked_at: str = ""
    expires_at: str = ""


@dataclass(frozen=True)
class ReplayDecision:
    accepted: bool
    authenticated: bool
    atomic: bool
    authority_identity: str
    denial_code: str = ""
    attestation: AuthorityAttestation | None = None


@dataclass(frozen=True)
class EvidenceBytes:
    reference: str
    data: bytes
    authenticated: bool
    immutable: bool
    custodian_identity: str


@dataclass(frozen=True)
class AuthorityAttestation:
    authority_identity: str
    authenticated: bool
    externally_governed: bool
    configuration_reference: str
    authentication_reference: str


class UnavailableSignatureValidator:
    def verify(self, payload: bytes, envelope: dict[str, Any]) -> SignatureResult:
        raise ManifestError("signature_validation_provider_unavailable")


class UnavailableStatusProvider:
    def status(self, manifest_digest: str, signer_identity: str, candidate: dict[str, Any] | None = None) -> StatusResult:
        raise ManifestError("revocation_status_provider_unavailable")


class UnavailableEvidenceVerifier:
    def verify(self, evidence: dict[str, Any], subject_digest: str) -> None:
        raise ManifestError("cryptographic_evidence_verifier_unavailable")


class UnavailableReplayAuthority:
    def consume(self, **_: Any) -> ReplayDecision:
        raise ManifestError("replay_authority_unavailable")


class UnavailableEvidenceRetriever:
    def retrieve(self, reference: str) -> EvidenceBytes:
        raise ManifestError("evidence_retriever_unavailable")


class UnavailableRevocationAuthority:
    def verify(self, response: dict[str, Any]) -> bool:
        raise ManifestError("revocation_authority_unavailable")


class UnavailableTransparencyAuthority:
    def verify(self, response: dict[str, Any]) -> bool:
        raise ManifestError("transparency_authority_unavailable")


class UnavailableIdentityAuthority:
    def verify(self, claims: dict[str, Any]) -> dict[str, str]:
        raise ManifestError("identity_authority_unavailable")


class UnavailableTrustRootAuthority:
    def verify(self, reference: str, digest: str, root: dict[str, Any]) -> AuthorityAttestation:
        raise ManifestError("trust_root_authority_unavailable")


PROVIDER_PROTOCOL = "gate4-provider.v1"
AUTH_RESPONSE_PROTOCOL = "sentinel-dna.gate4.authenticated-response.v1"
AUTH_DOMAIN = b"sentinel-dna|gate4|authenticated-response|v1"
MAX_RESPONSE_LIFETIME_SECONDS = 15 * 60
CLOCK_SKEW_SECONDS = 5 * 60
CANDIDATE_FIELDS = {"commit_sha", "tree_sha", "sentinel_image_digests", "external_boundary_image_digests", "third_party_image_digests", "runtime_digest", "lockfile_digest", "browser_executable_digest", "browser_base_image_digest", "browserauth_bridge_digest", "activation_manifest_digest", "edge_configuration_digest", "tls_evidence_digest", "custody_package_digest", "release_manifest_digest"}
IDENTITY_FIELDS = {"sentinel_dna", "requester", "builder", "signer", "verifier", "approver", "runtime_provider", "evidence_producer", "evidence_retriever", "cryptographic_verifier", "release_authority"}
IDENTITY_INEQUALITIES = (("requester", "builder"), ("requester", "approver"), ("builder", "approver"), ("builder", "verifier"), ("signer", "approver"), ("signer", "cryptographic_verifier"), ("runtime_provider", "cryptographic_verifier"), ("evidence_producer", "verifier"), ("evidence_producer", "approver"), ("evidence_producer", "evidence_retriever"), ("evidence_producer", "cryptographic_verifier"), ("cryptographic_verifier", "approver"), ("sentinel_dna", "release_authority"))
PROVIDER_FORBIDDEN_PARTS = ("tests", "fixtures", "simulation", ".git", ".gate4", "pilot-evidence", "generated-evidence")


def _require_external_dependency(value: Any, label: str) -> None:
    if value.__class__.__name__.startswith("Unavailable"):
        return
    attestation = getattr(value, "attestation", None)
    if not isinstance(attestation, AuthorityAttestation) or not attestation.authenticated or not attestation.externally_governed or not attestation.configuration_reference or not attestation.authentication_reference:
        raise ManifestError(f"{label}:external_authentication_required")


def _cbor(value: Any) -> bytes:
    """Encode the protocol's restricted data model as canonical CBOR."""
    def head(major: int, length: int) -> bytes:
        if length < 24: return bytes([(major << 5) | length])
        if length < 256: return bytes([(major << 5) | 24, length])
        if length < 65536: return bytes([(major << 5) | 25]) + struct.pack(">H", length)
        if length < 2**32: return bytes([(major << 5) | 26]) + struct.pack(">I", length)
        return bytes([(major << 5) | 27]) + struct.pack(">Q", length)
    if value is None: return b"\xf6"
    if value is False: return b"\xf4"
    if value is True: return b"\xf5"
    if isinstance(value, int) and not isinstance(value, bool):
        return head(0, value) if value >= 0 else head(1, -1 - value)
    if isinstance(value, bytes): return head(2, len(value)) + value
    if isinstance(value, str):
        raw = value.encode("utf-8"); return head(3, len(raw)) + raw
    if isinstance(value, list): return head(4, len(value)) + b"".join(_cbor(item) for item in value)
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value): raise ManifestError("protocol:cbor_string_keys_required")
        pairs = sorted(((_cbor(key), _cbor(item)) for key, item in value.items()), key=lambda pair: (len(pair[0]), pair[0]))
        return head(5, len(pairs)) + b"".join(key + item for key, item in pairs)
    raise ManifestError("protocol:cbor_unsupported_type")


def canonical_protocol_bytes(value: dict[str, Any]) -> bytes:
    if not isinstance(value, dict): raise ManifestError("protocol:object_required")
    return _cbor(value)


def _cbor_decode(raw: bytes) -> Any:
    def read(offset: int) -> tuple[int, int]:
        initial = raw[offset]; major, info = initial >> 5, initial & 31; offset += 1
        if info < 24: return major, info
        width = {24: 1, 25: 2, 26: 4, 27: 8}.get(info)
        if width is None: raise ManifestError("protocol:cbor_indefinite_length_forbidden")
        return major, int.from_bytes(raw[offset:offset + width], "big")
    def parse(offset: int) -> tuple[Any, int]:
        start = offset; major, length = read(offset); offset += 1
        if raw[start] & 31 >= 24: offset += {24: 1, 25: 2, 26: 4, 27: 8}[raw[start] & 31]
        if major == 0: return length, offset
        if major == 1: return -1 - length, offset
        if major in (2, 3):
            data = raw[offset:offset + length]; end = offset + length
            if end > len(raw): raise ManifestError("protocol:cbor_truncated")
            return (data if major == 2 else data.decode("utf-8")), end
        if major == 4:
            result = []
            for _ in range(length): item, offset = parse(offset); result.append(item)
            return result, offset
        if major == 5:
            result = {}
            for _ in range(length):
                key, offset = parse(offset); value, offset = parse(offset)
                if not isinstance(key, str) or key in result: raise ManifestError("protocol:cbor_map_invalid")
                result[key] = value
            return result, offset
        if major == 7 and length in (20, 21, 22): return ({20: False, 21: True, 22: None}[length], offset)
        raise ManifestError("protocol:cbor_type_unsupported")
    value, end = parse(0)
    if end != len(raw): raise ManifestError("protocol:cbor_trailing_bytes")
    return value


def protocol_digest(value: dict[str, Any] | bytes) -> str:
    return "sha256:" + hashlib.sha256(canonical_protocol_bytes(value) if isinstance(value, dict) else value).hexdigest()


def validate_candidate_tuple(candidate: dict[str, Any]) -> None:
    if not isinstance(candidate, dict) or set(candidate) != CANDIDATE_FIELDS: raise ManifestError("candidate:tuple_incomplete")
    if not COMMIT_RE.fullmatch(candidate["commit_sha"]) or not COMMIT_RE.fullmatch(candidate["tree_sha"]): raise ManifestError("candidate:commit_or_tree_invalid")
    for key in ("sentinel_image_digests", "external_boundary_image_digests", "third_party_image_digests"):
        values = candidate[key]
        if not isinstance(values, list) or not values or any(not isinstance(value, str) or not DIGEST_RE.fullmatch(value) for value in values): raise ManifestError(f"candidate:{key}_invalid")
    for key in CANDIDATE_FIELDS - {"commit_sha", "tree_sha", "sentinel_image_digests", "external_boundary_image_digests", "third_party_image_digests"}:
        if not isinstance(candidate[key], str) or not DIGEST_RE.fullmatch(candidate[key]): raise ManifestError(f"candidate:{key}_invalid")


def validate_identity_claims(claims: dict[str, Any], authority: IdentityAuthority) -> dict[str, str]:
    verified = authority.verify(claims)
    if not isinstance(verified, dict) or set(verified) != IDENTITY_FIELDS or any(not isinstance(value, str) or not value for value in verified.values()): raise ManifestError("identity:claims_incomplete")
    for left, right in IDENTITY_INEQUALITIES:
        if verified.get(left) == verified.get(right): raise ManifestError(f"identity:separation_violation:{left}:{right}")
    return verified


def build_gate4_request(*, operation: str, subject_digest: str, candidate: dict[str, Any], request_id: str | None = None, nonce: bytes | None = None) -> dict[str, Any]:
    validate_candidate_tuple(candidate)
    request = {
        "protocol_version": AUTH_RESPONSE_PROTOCOL, "operation": operation,
        "request_id": request_id or str(uuid.uuid4()), "nonce": nonce or secrets.token_bytes(32),
        "subject_digest": subject_digest, "candidate": candidate,
    }
    if not isinstance(request["nonce"], bytes) or len(request["nonce"]) != 32: raise ManifestError("request:nonce_entropy_invalid")
    request["request_hash"] = protocol_digest(canonical_protocol_bytes(request))
    return request


def _ed25519_verify(public_key: bytes, signature: bytes, message: bytes) -> bool:
    """Small dependency-free Ed25519 verifier for externally supplied public keys."""
    if len(public_key) != 32 or len(signature) != 64: return False
    p = 2**255 - 19; q = 2**252 + 27742317777372353535851937790883648493; d = (-121665 * pow(121666, p - 2, p)) % p
    I = pow(2, (p - 1) // 4, p)
    def xrecover(y: int) -> int:
        xx = (y*y - 1) * pow(d*y*y + 1, p - 2, p) % p; x = pow(xx, (p + 3)//8, p)
        if (x*x - xx) % p: x = (x * I) % p
        return x if x & 1 == 0 else p - x
    def decode(raw: bytes) -> tuple[int, int] | None:
        y = int.from_bytes(raw, "little") & ((1 << 255) - 1); x = xrecover(y)
        if y >= p or (y*y - x*x - 1 - d*x*x*y*y) % p: return None
        if (raw[31] >> 7) != (x & 1): x = p - x
        return x, y
    def add(P: tuple[int, int], Q: tuple[int, int]) -> tuple[int, int]:
        x1,y1=P; x2,y2=Q; den = pow(1+d*x1*x2*y1*y2, p-2, p); den2 = pow(1-d*x1*x2*y1*y2, p-2, p)
        return ((x1*y2+x2*y1)*den % p, (y1*y2+x1*x2)*den2 % p)
    def mul(P: tuple[int, int], n: int) -> tuple[int, int]:
        R=(0,1)
        while n:
            if n & 1: R=add(R,P)
            P=add(P,P); n >>= 1
        return R
    A = decode(public_key); R = decode(signature[:32])
    if A is None or R is None: return False
    B = (xrecover(4 * pow(5, p-2, p) % p), 4 * pow(5, p-2, p) % p)
    h = int.from_bytes(hashlib.sha512(Raw := signature[:32] + public_key + message).digest(), "little") % q
    return mul(B, int.from_bytes(signature[32:], "little")) == add(R, mul(A, h))


def _read_external_json(path_value: str, label: str) -> dict[str, Any]:
    path = _provider_path(path_value, Path.cwd())
    try: value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc: raise ManifestError(f"{label}:unreadable") from exc
    if not isinstance(value, dict): raise ManifestError(f"{label}:object_required")
    return value


def _consume_external_replay(authority: ReplayAuthority, *, request: dict[str, Any], provider_identity: str, authority_identity: str) -> None:
    _require_external_dependency(authority, "replay_authority")
    candidate_digest = protocol_digest(canonical_protocol_bytes(request["candidate"]))
    decision = authority.consume(authority_identity=authority_identity, provider_identity=provider_identity, operation=request["operation"], request_id=request["request_id"], nonce=request["nonce"], request_hash=request["request_hash"], subject_digest=request["subject_digest"], candidate_tuple_digest=candidate_digest)
    attestation = decision.attestation if isinstance(decision, ReplayDecision) else None
    if not isinstance(decision, ReplayDecision) or not decision.authenticated or not decision.authority_identity or decision.authority_identity != authority_identity or not decision.atomic or not isinstance(attestation, AuthorityAttestation) or not attestation.authenticated or not attestation.externally_governed or attestation.authority_identity != authority_identity or not attestation.configuration_reference or not attestation.authentication_reference:
        raise ManifestError("replay_authority:unauthenticated_or_non_atomic")
    if not decision.accepted:
        raise ManifestError("provider_denial:" + (decision.denial_code or "REQUEST_REPLAYED"))


def verify_independent_evidence(response: dict[str, Any], retriever: EvidenceRetriever) -> str:
    if retriever.__class__.__name__.startswith("Unavailable"):
        raise ManifestError("evidence_retriever_unavailable")
    _require_external_dependency(retriever, "evidence_retriever")
    reference = response.get("evidence_reference")
    if not isinstance(reference, str) or not reference or "://" not in reference or not re.search(r"(?:\?|&)digest=sha256:[0-9a-f]{64}(?:&|$)", reference):
        raise ManifestError("evidence:immutable_reference_required")
    evidence = retriever.retrieve(reference)
    if not isinstance(evidence, EvidenceBytes) or evidence.reference != reference or not evidence.authenticated or not evidence.immutable or not evidence.custodian_identity:
        raise ManifestError("evidence:authenticated_immutable_retrieval_required")
    computed = "sha256:" + hashlib.sha256(evidence.data).hexdigest()
    reference_digest = re.search(r"(?:\?|&)digest=(sha256:[0-9a-f]{64})(?:&|$)", reference).group(1)
    if reference_digest != response.get("evidence_digest"):
        raise ManifestError("evidence:reference_digest_mismatch")
    if computed != response.get("evidence_digest"):
        raise ManifestError("evidence:digest_mismatch")
    return computed


def verify_authenticated_response(response: dict[str, Any], request: dict[str, Any], *, trust_root: dict[str, Any], replay_authority: ReplayAuthority, evidence_retriever: EvidenceRetriever | None = None, revocation_authority: RevocationAuthority | None = None, transparency_authority: TransparencyAuthority | None = None, identity_authority: IdentityAuthority | None = None, expected_provider_identity: str | None = None, now: datetime | None = None, replay_already_consumed: bool = False) -> dict[str, Any]:
    required = {"protocol_version", "operation", "request_id", "nonce", "request_hash", "subject_digest", "candidate", "evidence_reference", "evidence_digest", "provider_identity", "provider_version", "verifier_identity", "verification_method_identity", "verification_method_version", "verified_at", "expires_at", "revocation_status", "approval_reference", "transparency_reference", "decision", "denial_code", "signature_algorithm", "signing_key_id", "trust_root_reference", "identity_claims", "signature"}
    if set(response) != required: raise ManifestError("response:fields_invalid")
    unsigned = {key: response[key] for key in response if key != "signature"}
    request_without_hash = {key: request[key] for key in request if key != "request_hash"}
    if request.get("request_hash") != protocol_digest(canonical_protocol_bytes(request_without_hash)): raise ManifestError("request:hash_invalid")
    if not isinstance(request.get("nonce"), bytes) or len(request["nonce"]) != 32: raise ManifestError("request:nonce_entropy_invalid")
    validate_candidate_tuple(request.get("candidate"))
    if response["protocol_version"] != AUTH_RESPONSE_PROTOCOL or response["operation"] != request["operation"]: raise ManifestError("response:operation_mismatch")
    if response["request_id"] != request["request_id"] or response["nonce"] != request["nonce"] or response["request_hash"] != request["request_hash"]: raise ManifestError("response:request_binding_mismatch")
    if response["subject_digest"] != request["subject_digest"] or response["candidate"] != request["candidate"]: raise ManifestError("response:subject_or_candidate_mismatch")
    if response["signature_algorithm"] != "Ed25519" or not response["transparency_reference"] or response["revocation_status"] != "ACTIVE": raise ManifestError("response:trust_evidence_missing")
    if response["trust_root_reference"] != trust_root.get("reference") or not expected_provider_identity or response["provider_identity"] != expected_provider_identity: raise ManifestError("response:provider_or_trust_root_mismatch")
    if response["decision"] not in {"APPROVED", "DENIED"}: raise ManifestError("response:decision_invalid")
    try:
        verified = datetime.strptime(response["verified_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        expires = datetime.strptime(response["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError) as exc: raise ManifestError("response:timestamp_invalid") from exc
    current = now or datetime.now(timezone.utc)
    if expires <= verified or (expires - verified).total_seconds() > MAX_RESPONSE_LIFETIME_SECONDS or verified - current > timedelta(seconds=CLOCK_SKEW_SECONDS) or current - expires > timedelta(seconds=CLOCK_SKEW_SECONDS): raise ManifestError("response:stale_or_expired")
    root_digest = trust_root.get("digest"); key_id = response["signing_key_id"]
    if trust_root.get("version") is None or not DIGEST_RE.fullmatch(root_digest or "") or trust_root.get("status") != "ACTIVE": raise ManifestError("trust_root:invalid")
    keys = trust_root.get("keys", {}); public = keys.get(key_id) if isinstance(keys, dict) else None
    if not isinstance(public, str): raise ManifestError("trust_root:key_unknown")
    try: public_key = base64.b64decode(public, validate=True); signature = base64.b64decode(response["signature"], validate=True)
    except Exception as exc: raise ManifestError("response:signature_encoding_invalid") from exc
    signed = AUTH_DOMAIN + hashlib.sha256(canonical_protocol_bytes(request)).digest() + canonical_protocol_bytes(unsigned)
    if not _ed25519_verify(public_key, signature, signed): raise ManifestError("response:signature_invalid")
    if not replay_already_consumed:
        _consume_external_replay(replay_authority, request=request, provider_identity=response["provider_identity"], authority_identity=getattr(replay_authority, "authority_identity", ""))
    verify_independent_evidence(response, evidence_retriever or UnavailableEvidenceRetriever())
    if not (revocation_authority or UnavailableRevocationAuthority()).verify(response): raise ManifestError("revocation:independent_verification_failed")
    if not (transparency_authority or UnavailableTransparencyAuthority()).verify(response): raise ManifestError("transparency:independent_verification_failed")
    validate_identity_claims(response["identity_claims"], identity_authority or UnavailableIdentityAuthority())
    if response["decision"] == "DENIED": raise ManifestError("provider_denial:" + str(response.get("denial_code", "unspecified")))
    return response


def _provider_path(path_value: str, repository_root: Path) -> Path:
    if not isinstance(path_value, str) or not path_value.strip():
        raise ManifestError("provider_path:required")
    path = Path(path_value).expanduser()
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ManifestError("provider_path:unavailable") from exc
    root = repository_root.resolve()
    try:
        resolved.relative_to(root)
        raise ManifestError("provider_path:repository_local")
    except ValueError:
        pass
    lowered = {part.casefold() for part in resolved.parts}
    if lowered.intersection(PROVIDER_FORBIDDEN_PARTS):
        raise ManifestError("provider_path:fixture_or_simulation")
    if not resolved.is_file():
        raise ManifestError("provider_path:regular_file_required")
    return resolved


def _provider_entry(config: dict[str, Any], repository_root: Path, scope: str) -> tuple[Path, dict[str, Any]]:
    required = ("identity", "version", "executable_digest", "protocol_version", "verification_scope", "trust_policy_scope", "trust_policy_reference", "status_authority_reference", "trust_root_reference", "trust_root_digest", "trust_root_version", "trust_root_authentication_reference", "replay_authority_identity", "replay_authority_reference", "evidence_retriever_identity", "evidence_retriever_reference", "revocation_authority_reference", "transparency_authority_reference")
    if any(not isinstance(config.get(key), str) or not config[key].strip() for key in required):
        raise ManifestError("provider_config:malformed")
    if config["protocol_version"] != PROVIDER_PROTOCOL:
        raise ManifestError("provider_config:unsupported_protocol")
    if scope not in config["verification_scope"].split(","):
        raise ManifestError("provider_config:scope_mismatch")
    allowlist_path_value = os.environ.get("GATE4_PROVIDER_ALLOWLIST_PATH")
    allowlist_digest = os.environ.get("GATE4_PROVIDER_ALLOWLIST_SHA256")
    if not allowlist_path_value or not re.fullmatch(r"sha256:[0-9a-f]{64}", allowlist_digest or ""):
        raise ManifestError("provider_allowlist:unavailable")
    allowlist_path = _provider_path(allowlist_path_value, repository_root)
    raw_allowlist = allowlist_path.read_bytes()
    if "sha256:" + hashlib.sha256(raw_allowlist).hexdigest() != allowlist_digest:
        raise ManifestError("provider_allowlist:digest_mismatch")
    try:
        allowlist = json.loads(raw_allowlist.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError("provider_allowlist:invalid") from exc
    entries = allowlist.get("providers") if isinstance(allowlist, dict) else None
    if not isinstance(entries, list):
        raise ManifestError("provider_allowlist:providers_required")
    entry = next((item for item in entries if isinstance(item, dict) and item.get("identity") == config["identity"] and item.get("version") == config["version"]), None)
    if entry is None or any(entry.get(key) != config.get(key) for key in required):
        raise ManifestError("provider_allowlist:provider_not_approved")
    for key in ("valid_from", "expires_at"):
        if not isinstance(entry.get(key), str) or not UTC_RE.fullmatch(entry[key]):
            raise ManifestError("provider_allowlist:validity_window_invalid")
    now = datetime.now(timezone.utc)
    valid_from = datetime.strptime(entry["valid_from"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    expires_at = datetime.strptime(entry["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if valid_from >= expires_at or now < valid_from or now >= expires_at:
        raise ManifestError("provider_allowlist:stale_or_not_yet_valid")
    trust_policy_reference = os.environ.get("GATE4_PROVIDER_TRUST_POLICY_REFERENCE")
    status_authority_reference = os.environ.get("GATE4_PROVIDER_STATUS_AUTHORITY_REFERENCE")
    if not trust_policy_reference or not status_authority_reference:
        raise ManifestError("provider_authority_reference:unavailable")
    if config.get("trust_policy_reference") != trust_policy_reference or entry.get("trust_policy_reference") != trust_policy_reference:
        raise ManifestError("provider_allowlist:trust_policy_scope_mismatch")
    if config.get("status_authority_reference") != status_authority_reference or entry.get("status_authority_reference") != status_authority_reference:
        raise ManifestError("provider_allowlist:status_authority_scope_mismatch")
    provider_path = _provider_path(config.get("path", ""), repository_root)
    if "sha256:" + hashlib.sha256(provider_path.read_bytes()).hexdigest() != config["executable_digest"]:
        raise ManifestError("provider:digest_mismatch")
    return provider_path, entry


def _provider_call(path: Path, config: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [str(path), "--protocol", PROVIDER_PROTOCOL],
            input=canonical_protocol_bytes(request),
            text=False,
            capture_output=True,
            timeout=30,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ManifestError("provider:unavailable") from exc
    if completed.returncode != 0 or completed.stderr or not completed.stdout:
        raise ManifestError("provider:verification_failed")
    try:
        result = _cbor_decode(completed.stdout)
    except (ManifestError, TypeError) as exc:
        raise ManifestError("provider:invalid_result") from exc
    if not isinstance(result, dict):
        raise ManifestError("provider:invalid_result")
    return result


def candidate_tuple_from_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return the complete immutable candidate tuple used by all providers."""
    artifacts = manifest.get("artifacts", {})
    def digests(name: str) -> list[str]:
        return sorted(item["digest"] for item in artifacts.get(name, []) if isinstance(item, dict) and isinstance(item.get("digest"), str))
    browser = artifacts.get("trusted_browser", {})
    return {
        "commit_sha": manifest.get("commit_sha"), "tree_sha": manifest.get("tree_sha"),
        "sentinel_image_digests": digests("sentinel_built_images"),
        "external_boundary_image_digests": digests("external_boundary_images"),
        "third_party_image_digests": digests("third_party_images"),
        "runtime_digest": artifacts.get("runtime", artifacts.get("playwright_runtime", {})).get("digest"),
        "lockfile_digest": artifacts.get("runtime", artifacts.get("playwright_runtime", {})).get("lockfile_digest"),
        "browser_executable_digest": browser.get("executable", {}).get("digest"),
        "browser_base_image_digest": browser.get("base_image_digest", browser.get("executable", {}).get("base_image_digest")),
        "browserauth_bridge_digest": artifacts.get("browserauth_bridge", artifacts.get("browserauth", {})).get("digest"),
        "activation_manifest_digest": manifest.get("activation_manifest", {}).get("instance_sha256"),
        "edge_configuration_digest": artifacts.get("edge_configuration", artifacts.get("deployment", {})).get("digest"),
        "tls_evidence_digest": artifacts.get("edge_tls", artifacts.get("tls_certified_origin", {})).get("certificate_digest", artifacts.get("tls_certified_origin", {}).get("digest")),
        "custody_package_digest": manifest.get("custody_package", {}).get("digest"),
        "release_manifest_digest": manifest_digest(manifest),
    }


def _load_provider_config(path_value: str | None) -> dict[str, Any] | None:
    if not path_value:
        return None
    try:
        config_path = Path(path_value).expanduser().resolve(strict=True)
        repository_root = Path.cwd().resolve()
        try:
            config_path.relative_to(repository_root)
            raise ManifestError("provider_config:repository_local")
        except ValueError:
            pass
        raw = config_path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raise ManifestError("provider_config:bom_forbidden")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError("provider_config:unreadable_or_invalid") from exc
    if not isinstance(value, dict):
        raise ManifestError("provider_config:object_required")
    return value


def _load_trust_root(config: dict[str, Any], authority: TrustRootAuthority | None = None) -> dict[str, Any]:
    reference = config.get("trust_root_reference")
    expected = config.get("trust_root_digest")
    if not isinstance(reference, str) or not isinstance(expected, str) or not DIGEST_RE.fullmatch(expected):
        raise ManifestError("trust_root:reference_or_digest_missing")
    root = _read_external_json(reference, "trust_root")
    raw = Path(reference).resolve(strict=True).read_bytes()
    if "sha256:" + hashlib.sha256(raw).hexdigest() != expected: raise ManifestError("trust_root:digest_mismatch")
    if root.get("version") != config.get("trust_root_version") or root.get("status") != "ACTIVE": raise ManifestError("trust_root:version_or_status_invalid")
    if any(not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9._:-]+", key) for key in root.get("keys", {})): raise ManifestError("trust_root:key_id_invalid")
    attestation = (authority or UnavailableTrustRootAuthority()).verify(reference, expected, root)
    if not isinstance(attestation, AuthorityAttestation) or not attestation.authenticated or not attestation.externally_governed or attestation.configuration_reference != reference or not attestation.authentication_reference:
        raise ManifestError("trust_root:independent_authentication_required")
    root = dict(root); root["reference"] = reference
    return root


class ExternalSignatureValidator:
    def __init__(self, config: dict[str, Any], repository_root: Path, evidence_verifier: EvidenceVerifier | None = None, replay_authority: ReplayAuthority | None = None, evidence_retriever: EvidenceRetriever | None = None, trust_root_authority: TrustRootAuthority | None = None, revocation_authority: RevocationAuthority | None = None, transparency_authority: TransparencyAuthority | None = None, identity_authority: IdentityAuthority | None = None, test_only: bool = False):
        if not test_only and any(value is not None for value in (evidence_verifier, replay_authority, evidence_retriever, trust_root_authority, revocation_authority, transparency_authority, identity_authority)):
            raise ManifestError("production_dependency_injection_forbidden")
        if test_only and os.environ.get("GATE4_CERTIFICATION_PATH", "").casefold() == "true":
            raise ManifestError("test_only:forbidden_on_certification_path")
        self.config = config
        self.path, self.allowlist_entry = _provider_entry(config, repository_root, "release-manifest-dsse")
        self.evidence_verifier = evidence_verifier or UnavailableEvidenceVerifier()
        self.replay_authority = replay_authority or UnavailableReplayAuthority()
        self.evidence_retriever = evidence_retriever or UnavailableEvidenceRetriever()
        _require_external_dependency(self.replay_authority, "replay_authority")
        _require_external_dependency(self.evidence_retriever, "evidence_retriever")
        self.trust_root = _load_trust_root(config, trust_root_authority)
        self.revocation_authority = revocation_authority or UnavailableRevocationAuthority()
        self.transparency_authority = transparency_authority or UnavailableTransparencyAuthority()
        self.identity_authority = identity_authority or UnavailableIdentityAuthority()
        _require_external_dependency(self.revocation_authority, "revocation_authority")
        _require_external_dependency(self.transparency_authority, "transparency_authority")
        _require_external_dependency(self.identity_authority, "identity_authority")

    def verify(self, payload: bytes, envelope: dict[str, Any]) -> SignatureResult:
        manifest = json.loads(payload.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
        request = build_gate4_request(operation="SignatureValidator.verify", subject_digest=manifest_digest(payload), candidate=candidate_tuple_from_manifest(manifest))
        _consume_external_replay(self.replay_authority, request=request, provider_identity=self.config["identity"], authority_identity=self.config["replay_authority_identity"])
        result = _provider_call(self.path, self.config, request)
        verify_authenticated_response(result, request, trust_root=self.trust_root, replay_authority=self.replay_authority, evidence_retriever=self.evidence_retriever, revocation_authority=self.revocation_authority, transparency_authority=self.transparency_authority, identity_authority=self.identity_authority, expected_provider_identity=self.config["identity"], replay_already_consumed=True)
        required = ("status", "subject_digest", "signer_identity", "issuer", "transparency_reference", "revocation_status", "verification_reference", "verified_at", "verification_method_identity", "verification_method_version")
        if any(not isinstance(result.get(key), str) or not result[key].strip() for key in required):
            raise ManifestError("provider:evidence_incomplete")
        if result["status"] != "VERIFIED" or result["subject_digest"] != manifest_digest(payload) or result["revocation_status"] != "ACTIVE":
            raise ManifestError("provider:evidence_not_verified")
        if result["verification_method_identity"] != self.config["identity"] or result["verification_method_version"] != self.config["version"]:
            raise ManifestError("provider:method_mismatch")
        verify_independent_evidence(result, self.evidence_retriever)
        self.evidence_verifier.verify(result, result["evidence_digest"])
        return SignatureResult(True, result["signer_identity"], result["issuer"], result["transparency_reference"], result["verification_reference"], result["verified_at"], result["revocation_status"], result["verification_method_identity"], result["verification_method_version"])


class ExternalStatusProvider:
    def __init__(self, config: dict[str, Any], repository_root: Path, evidence_verifier: EvidenceVerifier | None = None, replay_authority: ReplayAuthority | None = None, evidence_retriever: EvidenceRetriever | None = None, trust_root_authority: TrustRootAuthority | None = None, revocation_authority: RevocationAuthority | None = None, transparency_authority: TransparencyAuthority | None = None, identity_authority: IdentityAuthority | None = None, test_only: bool = False):
        if not test_only and any(value is not None for value in (evidence_verifier, replay_authority, evidence_retriever, trust_root_authority, revocation_authority, transparency_authority, identity_authority)):
            raise ManifestError("production_dependency_injection_forbidden")
        if test_only and os.environ.get("GATE4_CERTIFICATION_PATH", "").casefold() == "true":
            raise ManifestError("test_only:forbidden_on_certification_path")
        self.config = config
        self.path, self.allowlist_entry = _provider_entry(config, repository_root, "release-manifest-status")
        self.evidence_verifier = evidence_verifier or UnavailableEvidenceVerifier()
        self.replay_authority = replay_authority or UnavailableReplayAuthority()
        self.evidence_retriever = evidence_retriever or UnavailableEvidenceRetriever()
        _require_external_dependency(self.replay_authority, "replay_authority")
        _require_external_dependency(self.evidence_retriever, "evidence_retriever")
        self.trust_root = _load_trust_root(config, trust_root_authority)
        self.revocation_authority = revocation_authority or UnavailableRevocationAuthority()
        self.transparency_authority = transparency_authority or UnavailableTransparencyAuthority()
        self.identity_authority = identity_authority or UnavailableIdentityAuthority()
        _require_external_dependency(self.revocation_authority, "revocation_authority")
        _require_external_dependency(self.transparency_authority, "transparency_authority")
        _require_external_dependency(self.identity_authority, "identity_authority")

    def status(self, manifest_digest: str, signer_identity: str, candidate: dict[str, Any] | None = None) -> StatusResult:
        if candidate is None: raise ManifestError("candidate:tuple_required")
        request = build_gate4_request(operation="StatusProvider.status", subject_digest=manifest_digest, candidate=candidate)
        _consume_external_replay(self.replay_authority, request=request, provider_identity=self.config["identity"], authority_identity=self.config["replay_authority_identity"])
        result = _provider_call(self.path, self.config, request)
        verify_authenticated_response(result, request, trust_root=self.trust_root, replay_authority=self.replay_authority, evidence_retriever=self.evidence_retriever, revocation_authority=self.revocation_authority, transparency_authority=self.transparency_authority, identity_authority=self.identity_authority, expected_provider_identity=self.config["identity"], replay_already_consumed=True)
        required = ("status", "subject_digest", "signer_identity", "issuer", "transparency_reference", "revocation_status", "verification_reference", "verified_at", "authority_reference", "checked_at", "expires_at", "verification_method_identity", "verification_method_version")
        if any(not isinstance(result.get(key), str) or not result[key].strip() for key in required):
            raise ManifestError("status:evidence_incomplete")
        if result["status"] != "ACTIVE" or result["subject_digest"] != manifest_digest or result["signer_identity"] != signer_identity or result["revocation_status"] != "ACTIVE" or result["verification_method_identity"] != self.config["identity"] or result["verification_method_version"] != self.config["version"]:
            raise ManifestError("status:not_active")
        verify_independent_evidence(result, self.evidence_retriever)
        self.evidence_verifier.verify(result, result["evidence_digest"])
        return StatusResult(result["status"], result["authority_reference"], result["checked_at"], result["expires_at"])


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError("json:duplicate_key")
        result[key] = value
    return result


def _reject_forbidden_keys(value: Any, path: str = "manifest") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if FORBIDDEN_KEY_RE.search(key):
                raise ManifestError(f"{path}.{key}:forbidden_secret_field")
            _reject_forbidden_keys(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_forbidden_keys(item, f"{path}[{index}]")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        raise ManifestError(f"{path}:numeric_values_forbidden")


def _reject_unknown_keys(value: Any, allowed: dict[str, set[str]], path: str = "manifest") -> None:
    if isinstance(value, dict):
        permitted = allowed.get(path) or allowed.get(re.sub(r"\[\d+\]", "[]", path))
        if permitted is not None:
            unknown = set(value) - permitted
            if unknown:
                raise ManifestError(f"{path}.{sorted(unknown)[0]}:unknown_field")
        for key, item in value.items():
            child = f"{path}.{key}"
            _reject_unknown_keys(item, allowed, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_unknown_keys(item, allowed, f"{path}[{index}]")


def _normalise_arrays(value: Any, path: str = "", key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {name: _normalise_arrays(item, f"{path}.{name}".strip("."), name) for name, item in value.items()}
    if isinstance(value, list):
        items = [_normalise_arrays(item, path) for item in value]
        key = ARRAY_SORT_KEYS.get(path)
        if key:
            if any(not isinstance(item, dict) or not isinstance(item.get(key), str) for item in items):
                raise ManifestError(f"{path}:deterministic_sort_key_required")
            return sorted(items, key=lambda item: item[key])
        return items
    if isinstance(value, str) and key and key.endswith("_at"):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ManifestError(f"{path}:timestamp_invalid") from exc
        if parsed.tzinfo is None:
            raise ManifestError(f"{path}:timestamp_timezone_required")
        return parsed.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    return value


def canonical_bytes(manifest: dict[str, Any]) -> bytes:
    if not isinstance(manifest, dict):
        raise ManifestError("manifest:object_required")
    _reject_forbidden_keys(manifest)
    normalized = _normalise_arrays(copy.deepcopy(manifest))
    return json.dumps(normalized, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def manifest_digest(manifest_or_bytes: dict[str, Any] | bytes) -> str:
    payload = canonical_bytes(manifest_or_bytes) if isinstance(manifest_or_bytes, dict) else manifest_or_bytes
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _require(value: Any, path: str) -> None:
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{path}:required")


def _external_instance_path(path: Path, repository_root: Path) -> Path:
    if path.suffix.casefold() == ".mjs" or not path.is_absolute():
        raise ManifestError("activation_instance:path_not_external")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ManifestError("activation_instance:unavailable") from exc
    try:
        resolved.relative_to(repository_root.resolve())
        raise ManifestError("activation_instance:repository_local")
    except ValueError:
        pass
    forbidden = {"tests", "fixtures", "simulation", ".git", ".gate4", "pilot-evidence"}
    if {part.casefold() for part in resolved.parts}.intersection(forbidden):
        raise ManifestError("activation_instance:fixture_or_simulation")
    if not resolved.is_file():
        raise ManifestError("activation_instance:regular_file_required")
    return resolved


def _digest(value: Any, path: str) -> None:
    if not isinstance(value, str) or not DIGEST_RE.fullmatch(value):
        raise ManifestError(f"{path}:sha256_required")


def _image(item: Any, path: str, commit: str | None, tree: str | None, external: bool) -> None:
    if not isinstance(item, dict):
        raise ManifestError(f"{path}:object_required")
    for key in ("identity", "supplier", "signer"):
        _require(item.get(key), f"{path}.{key}")
    if MUTABLE_IMAGE_RE.search(item["identity"]):
        raise ManifestError(f"{path}.identity:mutable_image_reference")
    _digest(item.get("digest"), f"{path}.digest")
    provenance = item.get("provenance")
    if not isinstance(provenance, dict):
        raise ManifestError(f"{path}.provenance:required")
    _require(provenance.get("identity"), f"{path}.provenance.identity")
    _digest(provenance.get("digest"), f"{path}.provenance.digest")
    if external and ("source_commit" in item or "source_tree" in item):
        raise ManifestError(f"{path}:external_source_binding_forbidden")
    if not external and (item.get("source_commit") != commit or item.get("source_tree") != tree):
        raise ManifestError(f"{path}:source_binding_mismatch")


def validate_manifest_structure(manifest: dict[str, Any]) -> None:
    allowed = {
        "manifest": {"schema_version", "release_id", "repository", "commit_sha", "tree_sha", "activation_manifest", "custody_package", "artifacts", "target_platform", "created_at", "expires_at", "status", "revocation_status_reference", "supersedes_release_id"},
        "manifest.repository": {"owner", "name", "full_name", "repository_id"},
        "manifest.activation_manifest": {"validator_path", "validator_sha256", "instance_reference", "instance_sha256"},
        "manifest.custody_package": {"identity", "digest"},
        "manifest.artifacts": {"sentinel_built_images", "external_boundary_images", "third_party_images", "trusted_browser", "egress_policy", "tls_certified_origin", "browserauth", "sbom", "provenance", "deployment"},
        "manifest.artifacts.sentinel_built_images[]": {"identity", "digest", "source_commit", "source_tree", "supplier", "signer", "provenance"},
        "manifest.artifacts.external_boundary_images[]": {"identity", "digest", "supplier", "signer", "provenance"},
        "manifest.artifacts.third_party_images[]": {"identity", "digest", "supplier", "signer", "provenance"},
        "manifest.artifacts.trusted_browser": {"image", "playwright_version", "browser_revision", "browser_version", "executable"},
        "manifest.artifacts.trusted_browser.image": {"identity", "digest"},
        "manifest.artifacts.trusted_browser.executable": {"identity", "digest"},
        "manifest.artifacts.egress_policy": {"identity", "digest"},
        "manifest.artifacts.tls_certified_origin": {"identity", "digest"},
        "manifest.artifacts.browserauth": {"identity", "digest"},
        "manifest.artifacts.sbom": {"identity", "digest"},
        "manifest.artifacts.provenance[]": {"identity", "digest"},
        "manifest.artifacts.deployment": {"identity", "digest"},
        "manifest.artifacts.sentinel_built_images[].provenance": {"identity", "digest"},
        "manifest.artifacts.external_boundary_images[].provenance": {"identity", "digest"},
        "manifest.artifacts.third_party_images[].provenance": {"identity", "digest"},
    }
    _reject_unknown_keys(manifest, allowed)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError("schema_version:unsupported")
    for key in ("release_id", "commit_sha", "tree_sha", "created_at", "expires_at"):
        _require(manifest.get(key), key)
    commit, tree = manifest["commit_sha"], manifest["tree_sha"]
    if not COMMIT_RE.fullmatch(commit) or not COMMIT_RE.fullmatch(tree):
        raise ManifestError("release_identity:malformed")
    repository = manifest.get("repository")
    if not isinstance(repository, dict):
        raise ManifestError("repository:required")
    for key in ("owner", "name", "full_name", "repository_id"):
        _require(repository.get(key), f"repository.{key}")
    if repository["full_name"] != f"{repository['owner']}/{repository['name']}":
        raise ManifestError("repository.full_name:mismatch")
    activation = manifest.get("activation_manifest")
    if not isinstance(activation, dict) or activation.get("validator_path") != ACTIVATION_PATH:
        raise ManifestError("activation_manifest.validator_path:authoritative_path_required")
    _digest(activation.get("validator_sha256"), "activation_manifest.validator_sha256")
    _require(activation.get("instance_reference"), "activation_manifest.instance_reference")
    _digest(activation.get("instance_sha256"), "activation_manifest.instance_sha256")
    package = manifest.get("custody_package")
    if not isinstance(package, dict):
        raise ManifestError("custody_package:required")
    _require(package.get("identity"), "custody_package.identity")
    _digest(package.get("digest"), "custody_package.digest")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ManifestError("artifacts:required")
    for name in ("sentinel_built_images", "external_boundary_images", "third_party_images"):
        items = artifacts.get(name)
        if not isinstance(items, list) or not items:
            raise ManifestError(f"artifacts.{name}:required")
        for index, item in enumerate(items):
            _image(item, f"artifacts.{name}[{index}]", commit, tree, name != "sentinel_built_images")
    browser = artifacts.get("trusted_browser")
    if not isinstance(browser, dict):
        raise ManifestError("artifacts.trusted_browser:required")
    for key in ("playwright_version", "browser_revision", "browser_version"):
        _require(browser.get(key), f"artifacts.trusted_browser.{key}")
    for key in ("image", "executable"):
        item = browser.get(key)
        if not isinstance(item, dict):
            raise ManifestError(f"artifacts.trusted_browser.{key}:required")
        _require(item.get("identity"), f"artifacts.trusted_browser.{key}.identity")
        _digest(item.get("digest"), f"artifacts.trusted_browser.{key}.digest")
        if key == "image" and MUTABLE_IMAGE_RE.search(item["identity"]):
            raise ManifestError(f"artifacts.trusted_browser.{key}.identity:mutable_image_reference")
    for name in ("egress_policy", "tls_certified_origin", "browserauth", "sbom", "deployment"):
        item = artifacts.get(name)
        if not isinstance(item, dict):
            raise ManifestError(f"artifacts.{name}:required")
        _require(item.get("identity"), f"artifacts.{name}.identity")
        _digest(item.get("digest"), f"artifacts.{name}.digest")
    provenance = artifacts.get("provenance")
    if not isinstance(provenance, list) or not provenance:
        raise ManifestError("artifacts.provenance:required")
    for index, item in enumerate(provenance):
        _require(item.get("identity") if isinstance(item, dict) else None, f"artifacts.provenance[{index}].identity")
        _digest(item.get("digest") if isinstance(item, dict) else None, f"artifacts.provenance[{index}].digest")
    if manifest.get("status") != "ACTIVE":
        raise ManifestError("status:not_active")
    if not UTC_RE.fullmatch(manifest["created_at"]) or not UTC_RE.fullmatch(manifest["expires_at"]):
        raise ManifestError("timestamps:utc_required")
    if "revocation_status_reference" not in manifest:
        raise ManifestError("revocation_status_reference:required")


def load_canonical_manifest(path: Path, supplied_digest: str) -> tuple[dict[str, Any], bytes, str]:
    raw = path.read_bytes()
    try:
        if raw.startswith(b"\xef\xbb\xbf"):
            raise ManifestError("manifest:bom_forbidden")
        manifest = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError("manifest:invalid_json_or_encoding") from exc
    canonical = canonical_bytes(manifest)
    computed = manifest_digest(canonical)
    if supplied_digest != computed:
        raise ManifestError("manifest_digest:mismatch")
    if raw != canonical:
        raise ManifestError("manifest:noncanonical_bytes")
    normalized_manifest = json.loads(canonical.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    validate_manifest_structure(normalized_manifest)
    return normalized_manifest, canonical, computed


def validate_detached_signature(payload: bytes, envelope: dict[str, Any], validator: SignatureValidator, trust_policy: dict[str, Any]) -> SignatureResult:
    if not isinstance(envelope, dict) or envelope.get("scheme") != "dsse":
        raise ManifestError("signature_envelope:dsse_required")
    if envelope.get("payload_type") != "application/vnd.gate4.release-manifest.v1+json":
        raise ManifestError("signature_envelope:payload_type_mismatch")
    signature = envelope.get("signature")
    if not isinstance(signature, str):
        raise ManifestError("signature_envelope:signature_required")
    try:
        base64.b64decode(signature, validate=True)
    except Exception as exc:
        raise ManifestError("signature_envelope:signature_encoding_invalid") from exc
    result = validator.verify(payload, envelope)
    if not result.valid:
        raise ManifestError("signature:invalid")
    if result.signer_identity != trust_policy.get("trusted_signer_identity"):
        raise ManifestError("signer_trust:identity_mismatch")
    if result.issuer != trust_policy.get("trusted_issuer"):
        raise ManifestError("signer_trust:issuer_mismatch")
    if trust_policy.get("require_transparency", True) and not result.transparency_reference:
        raise ManifestError("signer_trust:transparency_required")
    return result


def authorize_release(*, manifest_path: Path, manifest_digest_input: str, signature_path: Path, repository: str, head_sha: str, tree_sha: str, validator_path: Path, activation_instance_path: Path, validator: SignatureValidator | None = None, status_provider: StatusProvider | None = None, trust_policy: dict[str, Any] | None = None, now: datetime | None = None) -> dict[str, str]:
    manifest, canonical, digest = verify_manifest_authority(manifest_path=manifest_path, manifest_digest_input=manifest_digest_input, signature_path=signature_path, repository=repository, validator=validator, status_provider=status_provider, trust_policy=trust_policy, now=now)
    if head_sha != manifest["commit_sha"]:
        raise ManifestError("HEAD:manifest_commit_mismatch")
    if tree_sha != manifest["tree_sha"]:
        raise ManifestError("HEAD_tree:manifest_tree_mismatch")
    if str(validator_path).replace("\\", "/") != ACTIVATION_PATH:
        raise ManifestError("activation_validator_path:authoritative_path_required")
    validator_digest = "sha256:" + hashlib.sha256(validator_path.read_bytes()).hexdigest()
    if validator_digest != manifest["activation_manifest"]["validator_sha256"]:
        raise ManifestError("activation_validator:digest_mismatch")
    instance = _external_instance_path(activation_instance_path, Path.cwd())
    actual_instance = "sha256:" + hashlib.sha256(instance.read_bytes()).hexdigest()
    if actual_instance != manifest["activation_manifest"]["instance_sha256"]:
        raise ManifestError("activation_instance:digest_mismatch")
    return {"manifest_digest": digest, "release_id": manifest["release_id"], "commit_sha": manifest["commit_sha"], "tree_sha": manifest["tree_sha"], "signer_identity": manifest["_verified_signer_identity"]}


def verify_manifest_authority(*, manifest_path: Path, manifest_digest_input: str, signature_path: Path, repository: str, validator: SignatureValidator | None = None, status_provider: StatusProvider | None = None, trust_policy: dict[str, Any] | None = None, now: datetime | None = None) -> tuple[dict[str, Any], bytes, str]:
    manifest, canonical, digest = load_canonical_manifest(manifest_path, manifest_digest_input)
    signature_raw = signature_path.read_bytes()
    if signature_raw.startswith(b"\xef\xbb\xbf"):
        raise ManifestError("signature_envelope:bom_forbidden")
    envelope = json.loads(signature_raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    policy = trust_policy or {}
    result = validate_detached_signature(canonical, envelope, validator or UnavailableSignatureValidator(), policy)
    now_value = now or datetime.now(timezone.utc)
    provider = status_provider or UnavailableStatusProvider()
    status_result = provider.status(digest, result.signer_identity, candidate_tuple_from_manifest(manifest)) if isinstance(provider, ExternalStatusProvider) else provider.status(digest, result.signer_identity)
    status = status_result if isinstance(status_result, str) else status_result.status
    if status != "ACTIVE":
        raise ManifestError("manifest_status:not_active")
    if isinstance(status_result, StatusResult):
        try:
            checked_at = datetime.strptime(status_result.checked_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            status_expires = datetime.strptime(status_result.expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise ManifestError("manifest_status:evidence_timestamp_invalid") from exc
        if checked_at > now_value or now_value >= status_expires:
            raise ManifestError("manifest_status:evidence_stale")
    expires = datetime.strptime(manifest["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if now_value >= expires:
        raise ManifestError("manifest:expired")
    if manifest["repository"]["full_name"] != repository:
        raise ManifestError("repository:mismatch")
    manifest = dict(manifest)
    manifest["_verified_signer_identity"] = result.signer_identity
    return manifest, canonical, digest


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Verify a Gate4 signed release manifest")
    parser.add_argument("manifest")
    parser.add_argument("--digest", required=True)
    parser.add_argument("--signature", required=True)
    parser.add_argument("--trust-policy")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--head")
    parser.add_argument("--tree")
    parser.add_argument("--validator-path")
    parser.add_argument("--activation-instance")
    parser.add_argument("--signature-provider-config")
    parser.add_argument("--status-provider-config")
    args = parser.parse_args()
    try:
        trust_policy = json.loads(Path(args.trust_policy).read_text(encoding="utf-8")) if args.trust_policy else {}
        if not isinstance(trust_policy, dict):
            raise ManifestError("trust_policy:object_required")
        signature_config = _load_provider_config(args.signature_provider_config)
        status_config = _load_provider_config(args.status_provider_config)
        signature_provider = ExternalSignatureValidator(signature_config, Path.cwd()) if signature_config else None
        status_provider = ExternalStatusProvider(status_config, Path.cwd()) if status_config else None
        if not args.head or not args.tree or not args.validator_path or not args.activation_instance:
            manifest, _, digest = verify_manifest_authority(manifest_path=Path(args.manifest), manifest_digest_input=args.digest, signature_path=Path(args.signature), repository=args.repository, validator=signature_provider, status_provider=status_provider, trust_policy=trust_policy)
            result = {"manifest_digest": digest, "release_id": manifest["release_id"], "commit_sha": manifest["commit_sha"], "tree_sha": manifest["tree_sha"]}
        else:
            result = authorize_release(manifest_path=Path(args.manifest), manifest_digest_input=args.digest, signature_path=Path(args.signature), repository=args.repository, head_sha=args.head, tree_sha=args.tree, validator_path=Path(args.validator_path), activation_instance_path=Path(args.activation_instance), validator=signature_provider, status_provider=status_provider, trust_policy=trust_policy)
    except (ManifestError, OSError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: {exc}")
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
