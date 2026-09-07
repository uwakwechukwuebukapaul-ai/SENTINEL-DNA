"""Fail-closed, non-secret validation of an externally supplied Gate4 package."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import os
from pathlib import Path
from typing import Any

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
IMAGE = re.compile(r"^\S+@sha256:[0-9a-f]{64}$")
PLATFORM = "linux/amd64"
SENTINEL_BUILT = {"application_image", "trusted_browser_image"}
EXTERNAL_SECURITY_BOUNDARY = {"egress_gateway_image", "edge_image"}
THIRD_PARTY = {"postgres_image", "redis_image"}
IMAGES = SENTINEL_BUILT | EXTERNAL_SECURITY_BOUNDARY | THIRD_PARTY
APPROVED = "INDEPENDENTLY_APPROVED"
STATUSES = {"MISSING", "PRESENT", "CLAIMED", "LOCALLY_VERIFIED", "EXTERNALLY_VERIFIED", APPROVED, "HISTORICAL", "CONFLICTING", "BLOCKED"}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _schema_check(value: Any, schema: dict[str, Any], root: dict[str, Any], path: str, errors: list[str]) -> None:
    if "$ref" in schema:
        target = root
        for part in schema["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        _schema_check(value, target, root, path, errors)
        return
    if "const" in schema and value != schema["const"]: errors.append(f"{path}:const")
    if "enum" in schema and value not in schema["enum"]: errors.append(f"{path}:enum")
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict): errors.append(f"{path}:object_required"); return
        for key in schema.get("required", []):
            if key not in value: errors.append(f"{path}.{key}:missing")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in schema.get("properties", {}): errors.append(f"{path}.{key}:unknown")
        for key, sub in schema.get("properties", {}).items():
            if key in value: _schema_check(value[key], sub, root, f"{path}.{key}", errors)
    elif kind == "array":
        if not isinstance(value, list): errors.append(f"{path}:array_required"); return
        for index, item in enumerate(value): _schema_check(item, schema.get("items", {}), root, f"{path}[{index}]", errors)
    elif kind == "string":
        if not isinstance(value, str): errors.append(f"{path}:string_required"); return
        if "minLength" in schema and len(value) < schema["minLength"]: errors.append(f"{path}:empty")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value): errors.append(f"{path}:pattern")


def _digest(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not SHA256.fullmatch(value): errors.append(f"{label}:sha256_required")


def _approved_record(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, dict): errors.append(f"{label}:missing"); return
    if value.get("status") != APPROVED: errors.append(f"{label}.status:independent_approval_required")
    if not isinstance(value.get("evidence_reference"), str) or not value["evidence_reference"].strip(): errors.append(f"{label}.evidence_reference:missing")
    _digest(value.get("evidence_digest"), f"{label}.evidence_digest", errors)
    for key in ("verifier_identity", "verification_method", "verification_method_identity", "verification_method_version", "approval_reference"):
        if not isinstance(value.get(key), str) or not value[key].strip(): errors.append(f"{label}.{key}:missing")
    if not isinstance(value.get("verified_at"), str) or not UTC.fullmatch(value["verified_at"]): errors.append(f"{label}.verified_at:utc_required")


def _signature(value: Any, label: str, artifact_digest: str, errors: list[str]) -> None:
    if not isinstance(value, dict): errors.append(f"{label}:missing"); return
    if value.get("status") != APPROVED: errors.append(f"{label}.status:independent_approval_required")
    if value.get("artifact_digest") != artifact_digest: errors.append(f"{label}.artifact_digest:mismatch")
    for key in ("signer_identity", "oidc_issuer", "transparency_log_reference"):
        if not isinstance(value.get(key), str) or not value[key].strip(): errors.append(f"{label}.{key}:missing")
    _approved_record(value.get("verification_record"), f"{label}.verification_record", errors)


def _attestation(value: Any, label: str, digest: str, commit: str, tree: str, errors: list[str], *, require_release_binding: bool = True) -> None:
    if not isinstance(value, dict): errors.append(f"{label}:missing"); return
    if value.get("status") != APPROVED: errors.append(f"{label}.status:independent_approval_required")
    if value.get("subject_digest") != digest: errors.append(f"{label}.subject_digest:mismatch")
    if require_release_binding and value.get("source_commit") != commit: errors.append(f"{label}.source_commit:mismatch")
    if require_release_binding and value.get("source_tree") != tree: errors.append(f"{label}.source_tree:mismatch")
    if value.get("platform") != PLATFORM: errors.append(f"{label}.platform:linux_amd64_required")
    for key in ("reference", "predicate_type", "source_repository", "builder_identity", "workflow_identity"):
        if not isinstance(value.get(key), str) or not value[key].strip(): errors.append(f"{label}.{key}:missing")
    if not isinstance(value.get("build_timestamp"), str) or not UTC.fullmatch(value["build_timestamp"]): errors.append(f"{label}.build_timestamp:utc_required")
    if not isinstance(value.get("materials"), list) or not value["materials"] or any(not isinstance(material, str) or not material.strip() for material in value["materials"]): errors.append(f"{label}.materials:meaningful_provenance_required")
    _approved_record(value.get("verification_record"), f"{label}.verification_record", errors)


def _sbom(value: Any, label: str, digest: str, errors: list[str]) -> None:
    if not isinstance(value, dict): errors.append(f"{label}:missing"); return
    if value.get("status") != APPROVED: errors.append(f"{label}.status:independent_approval_required")
    if value.get("artifact_digest") != digest: errors.append(f"{label}.artifact_digest:mismatch")
    _digest(value.get("document_digest"), f"{label}.document_digest", errors)
    if value.get("format") not in {"SPDX", "CycloneDX"}: errors.append(f"{label}.format:unsupported")
    if not isinstance(value.get("document_reference"), str) or not value["document_reference"].strip(): errors.append(f"{label}.document_reference:missing")
    _approved_record(value.get("verification_record"), f"{label}.verification_record", errors)


def _activation_bytes(path: Path | None, errors: list[str]) -> tuple[dict[str, Any] | None, bytes | None]:
    if path is None: errors.append("activation_manifest:bytes_required"); return None, None
    if path.suffix.casefold() == ".mjs" or not path.is_absolute():
        errors.append("activation_manifest:external_json_path_required"); return None, None
    try:
        resolved = path.resolve(strict=True)
        repository = Path(__file__).resolve().parents[3]
        resolved.relative_to(repository)
        errors.append("activation_manifest:repository_local")
        return None, None
    except ValueError:
        pass
    except OSError:
        errors.append("activation_manifest:unavailable"); return None, None
    forbidden = {"tests", "fixtures", "simulation", ".git", ".gate4", "pilot-evidence"}
    if {part.casefold() for part in resolved.parts}.intersection(forbidden):
        errors.append("activation_manifest:fixture_or_simulation"); return None, None
    try:
        raw = resolved.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raise ValueError("bom_forbidden")
        manifest = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except (OSError, ValueError, json.JSONDecodeError): errors.append("activation_manifest:bytes_unreadable"); return None, None
    if not isinstance(manifest, dict): errors.append("activation_manifest:object_required"); return None, raw
    return manifest, raw


def _external_verifier_config(path: Path) -> bool:
    try:
        resolved = path.resolve(strict=True)
        repository = Path(__file__).resolve().parents[3]
        resolved.relative_to(repository)
        return False
    except ValueError:
        pass
    except OSError:
        return False
    forbidden = {"tests", "fixtures", "simulation", ".git", ".gate4", "pilot-evidence", "generated-evidence"}
    return resolved.is_file() and not ({part.casefold() for part in resolved.parts} & forbidden)


def _configuration(value: Any, label: str, expected_commit: str, expected_tree: str, errors: list[str]) -> None:
    if not isinstance(value, dict): errors.append(f"{label}:missing"); return
    if value.get("artifact_class") != "REPOSITORY_CONFIGURATION": errors.append(f"{label}.artifact_class:mismatch")
    if value.get("source_commit") != expected_commit: errors.append(f"{label}.source_commit:mismatch")
    if value.get("source_tree") != expected_tree: errors.append(f"{label}.source_tree:mismatch")
    _digest(value.get("digest"), f"{label}.digest", errors)
    _approved_record(value.get("verification_record"), f"{label}.verification_record", errors)


def _tls(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, dict): errors.append(f"{label}:missing"); return
    if value.get("artifact_class") != "EXTERNAL_TLS_CUSTODY": errors.append(f"{label}.artifact_class:mismatch")
    if not isinstance(value.get("custody_reference"), str) or not value["custody_reference"].strip(): errors.append(f"{label}.custody_reference:missing")
    _digest(value.get("certificate_digest"), f"{label}.certificate_digest", errors)
    if not isinstance(value.get("private_key_custody_reference"), str) or not value["private_key_custody_reference"].strip(): errors.append(f"{label}.private_key_custody_reference:missing")
    match = value.get("certificate_key_match")
    if not isinstance(match, dict):
        errors.append(f"{label}.certificate_key_match:independent_evidence_required")
    else:
        if match.get("status") != APPROVED: errors.append(f"{label}.certificate_key_match.status:independent_approval_required")
        if match.get("certificate_digest") != value.get("certificate_digest"): errors.append(f"{label}.certificate_key_match.certificate_digest:mismatch")
        if match.get("private_key_custody_reference") != value.get("private_key_custody_reference"): errors.append(f"{label}.certificate_key_match.private_key_custody_reference:mismatch")
        if not isinstance(match.get("evidence_reference"), str) or not match["evidence_reference"].strip(): errors.append(f"{label}.certificate_key_match.evidence_reference:missing")
        _digest(match.get("evidence_digest"), f"{label}.certificate_key_match.evidence_digest", errors)
        for key in ("verifier_identity", "verification_method", "verification_method_identity", "verification_method_version", "approval_reference"):
            if not isinstance(match.get(key), str) or not match[key].strip(): errors.append(f"{label}.certificate_key_match.{key}:missing")
        if not isinstance(match.get("verified_at"), str) or not UTC.fullmatch(match["verified_at"]): errors.append(f"{label}.certificate_key_match.verified_at:utc_required")
    _approved_record(value.get("verification_record"), f"{label}.verification_record", errors)


def validate(package: dict, *, expected_commit: str, expected_tree: str, schema_path: Path | None = None, activation_manifest_path: Path | None = None, expected_application_image: str | None = None, expected_trusted_browser_image: str | None = None, expected_egress_image: str | None = None, expected_edge_image: str | None = None, require_external_verification: bool = True, test_only: bool = False) -> dict[str, object]:
    errors: list[str] = []
    if test_only and os.environ.get("GATE4_CERTIFICATION_PATH", "").casefold() == "true":
        errors.append("test_only:forbidden_on_certification_path")
    if require_external_verification and not test_only:
        # This repository deliberately contains no cryptographic authority.  A
        # production invocation must supply an independently authenticated
        # evidence verifier; structural custody records can never authorize.
        errors.append("cryptographic_evidence_verifier:unavailable")
    if not COMMIT.fullmatch(expected_commit) or not COMMIT.fullmatch(expected_tree): return {"status": "BLOCKED", "errors": ["expected_release_identity:malformed"], "secret_values_logged": False}
    if not isinstance(package, dict): return {"status": "BLOCKED", "errors": ["package:object_required"], "secret_values_logged": False}
    schema_file = schema_path or Path(__file__).resolve().parents[1] / "GATE4_EXTERNAL_CUSTODY.schema.json"
    try: schema = json.loads(schema_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return {"status": "BLOCKED", "errors": ["schema:unreadable_or_invalid"], "secret_values_logged": False}
    _schema_check(package, schema, schema, "package", errors)
    if package.get("schema_version") != "3.0": errors.append("schema_version:unsupported")
    release = package.get("release", {})
    if release.get("commit") != expected_commit: errors.append("release.commit:mismatch")
    if release.get("tree") != expected_tree: errors.append("release.tree:mismatch")
    policies = package.get("trust_policies", {})
    policy_classes = {"sentinel_built_images": SENTINEL_BUILT, "external_security_boundary_images": EXTERNAL_SECURITY_BOUNDARY, "third_party_images": THIRD_PARTY}
    policy_signers = [policies.get(key, {}).get("signer_identity") for key in policy_classes]
    if len(set(policy_signers)) != len(policy_signers): errors.append("trust_policies:signers_must_be_distinct")
    artifacts = package.get("artifacts", {})
    for name in IMAGES:
        item = artifacts.get(name)
        label = f"artifacts.{name}"
        if not isinstance(item, dict): continue
        digest = item.get("digest", "")
        if not IMAGE.fullmatch(item.get("reference", "")): errors.append(f"{label}.reference:immutable_digest_required")
        _digest(digest, f"{label}.digest", errors)
        if isinstance(item.get("reference"), str) and not item["reference"].endswith("@" + digest): errors.append(f"{label}:reference_digest_mismatch")
        expected_class = "SENTINEL_BUILT" if name in SENTINEL_BUILT else "EXTERNAL_SECURITY_BOUNDARY" if name in EXTERNAL_SECURITY_BOUNDARY else "THIRD_PARTY"
        if item.get("artifact_class") != expected_class: errors.append(f"{label}.artifact_class:mismatch")
        if not isinstance(item.get("supplier_identity"), str) or not item["supplier_identity"].strip(): errors.append(f"{label}.supplier_identity:missing")
        if name in SENTINEL_BUILT and (item.get("source_commit") != expected_commit or item.get("source_tree") != expected_tree): errors.append(f"{label}.source_binding:mismatch")
        if name in EXTERNAL_SECURITY_BOUNDARY:
            if item.get("source_commit") == expected_commit or item.get("source_tree") == expected_tree: errors.append(f"{label}.external_source_binding:must_not_claim_sentinel_release")
            if item.get("supplier_identity") in {"sentinel-dna", "Sentinel DNA"}: errors.append(f"{label}.supplier_identity:external_supplier_required")
        policy_name = "sentinel_built_images" if name in SENTINEL_BUILT else "external_security_boundary_images" if name in EXTERNAL_SECURITY_BOUNDARY else "third_party_images"
        signer_policy = policies.get(policy_name, {})
        if item.get("supplier_identity") != signer_policy.get("supplier_identity"): errors.append(f"{label}.supplier_identity:trust_policy_mismatch")
        if item.get("registry") != signer_policy.get("registry_identity"): errors.append(f"{label}.registry:trust_policy_mismatch")
        if isinstance(item.get("signature"), dict) and item["signature"].get("signer_identity") != signer_policy.get("signer_identity"): errors.append(f"{label}.signature.signer_identity:trust_policy_mismatch")
        _signature(item.get("signature"), f"{label}.signature", digest, errors)
        _attestation(item.get("attestation"), f"{label}.attestation", digest, expected_commit, expected_tree, errors, require_release_binding=name in SENTINEL_BUILT)
        if name in EXTERNAL_SECURITY_BOUNDARY and isinstance(item.get("attestation"), dict) and (item["attestation"].get("source_commit") == expected_commit or item["attestation"].get("source_tree") == expected_tree): errors.append(f"{label}.attestation:external_source_must_be_distinct")
        _sbom(item.get("sbom"), f"{label}.sbom", digest, errors)
        if name == "egress_gateway_image" and expected_egress_image and item.get("reference") != expected_egress_image: errors.append(f"{label}.reference:workflow_mismatch")
        if name == "edge_image" and expected_edge_image and item.get("reference") != expected_edge_image: errors.append(f"{label}.reference:workflow_mismatch")
        if name == "application_image" and expected_application_image and item.get("reference") != expected_application_image: errors.append(f"{label}.reference:workflow_mismatch")
        if name == "trusted_browser_image" and expected_trusted_browser_image and item.get("reference") != expected_trusted_browser_image: errors.append(f"{label}.reference:workflow_mismatch")
    runtime = artifacts.get("playwright_runtime", {})
    if isinstance(runtime, dict):
        _digest(runtime.get("digest"), "artifacts.playwright_runtime.digest", errors); _digest(runtime.get("lockfile_digest"), "artifacts.playwright_runtime.lockfile_digest", errors)
        _signature(runtime.get("signature"), "artifacts.playwright_runtime.signature", runtime.get("digest", ""), errors); _attestation(runtime.get("attestation"), "artifacts.playwright_runtime.attestation", runtime.get("digest", ""), expected_commit, expected_tree, errors)
    browser = artifacts.get("browser_executable", {})
    if isinstance(browser, dict):
        for key in ("digest", "base_image_digest"): _digest(browser.get(key), f"artifacts.browser_executable.{key}", errors)
        if browser.get("platform") != PLATFORM: errors.append("artifacts.browser_executable.platform:linux_amd64_required")
        _signature(browser.get("signature"), "artifacts.browser_executable.signature", browser.get("digest", ""), errors); _attestation(browser.get("attestation"), "artifacts.browser_executable.attestation", browser.get("digest", ""), expected_commit, expected_tree, errors)
    bridge = artifacts.get("browserauth_bridge", {})
    if isinstance(bridge, dict):
        _digest(bridge.get("digest"), "artifacts.browserauth_bridge.digest", errors); _signature(bridge.get("signature"), "artifacts.browserauth_bridge.signature", bridge.get("digest", ""), errors); _approved_record(bridge.get("verification_record"), "artifacts.browserauth_bridge.verification_record", errors)
    policy = artifacts.get("egress_policy", {})
    if isinstance(policy, dict):
        _digest(policy.get("digest"), "artifacts.egress_policy.digest", errors); _signature(policy.get("signature"), "artifacts.egress_policy.signature", policy.get("digest", ""), errors); _approved_record(policy.get("verification_record"), "artifacts.egress_policy.verification_record", errors)
    _configuration(artifacts.get("edge_configuration"), "artifacts.edge_configuration", expected_commit, expected_tree, errors)
    _tls(artifacts.get("edge_tls"), "artifacts.edge_tls", errors)
    activation = artifacts.get("activation_manifest", {})
    manifest, raw = _activation_bytes(activation_manifest_path, errors)
    if isinstance(activation, dict):
        _digest(activation.get("digest"), "artifacts.activation_manifest.digest", errors)
        if raw is not None and isinstance(activation.get("digest"), str) and activation["digest"] != "sha256:" + hashlib.sha256(raw).hexdigest(): errors.append("artifacts.activation_manifest.digest:bytes_mismatch")
        if activation.get("manifest_bytes_reference") != activation.get("reference"): errors.append("artifacts.activation_manifest:bytes_reference_mismatch")
        _signature(activation.get("signature"), "artifacts.activation_manifest.signature", activation.get("digest", ""), errors); _approved_record(activation.get("verification_record"), "artifacts.activation_manifest.verification_record", errors)
    if isinstance(manifest, dict):
        if manifest.get("registry_identity") != package.get("verification", {}).get("registry_identity"): errors.append("activation_manifest.registry_identity:mismatch")
        for evidence_key in ("signature_evidence_status", "attestation_evidence_status", "sbom_evidence_status"):
            if manifest.get(evidence_key) != APPROVED: errors.append(f"activation_manifest.{evidence_key}:independent_approval_required")
        expected_fields = {"release_commit": expected_commit, "release_tree": expected_tree, "application_image_digest": artifacts.get("application_image", {}).get("digest"), "trusted_browser_image_digest": artifacts.get("trusted_browser_image", {}).get("digest"), "egress_gateway_image_digest": artifacts.get("egress_gateway_image", {}).get("digest"), "edge_image_digest": artifacts.get("edge_image", {}).get("digest"), "postgres_image_digest": artifacts.get("postgres_image", {}).get("digest"), "redis_image_digest": artifacts.get("redis_image", {}).get("digest"), "egress_gateway_artifact_class": "EXTERNAL_SECURITY_BOUNDARY", "edge_artifact_class": "EXTERNAL_SECURITY_BOUNDARY", "approved_edge_configuration_digest": artifacts.get("edge_configuration", {}).get("digest"), "approved_edge_tls_custody_reference": artifacts.get("edge_tls", {}).get("custody_reference"), "approved_edge_tls_certificate_digest": artifacts.get("edge_tls", {}).get("certificate_digest"), "approved_edge_tls_private_key_custody_reference": artifacts.get("edge_tls", {}).get("private_key_custody_reference"), "approved_edge_tls_certificate_key_match_evidence_digest": artifacts.get("edge_tls", {}).get("certificate_key_match", {}).get("evidence_digest"), "approved_runtime_module_digest": artifacts.get("playwright_runtime", {}).get("digest"), "approved_runtime_dependency_lockfile_digest": artifacts.get("playwright_runtime", {}).get("lockfile_digest"), "approved_browser_executable_digest": artifacts.get("browser_executable", {}).get("digest"), "approved_browser_base_image_digest": artifacts.get("browser_executable", {}).get("base_image_digest"), "approved_browser_auth_bridge_digest": artifacts.get("browserauth_bridge", {}).get("digest"), "approved_egress_policy_digest": artifacts.get("egress_policy", {}).get("digest")}
        for key, value in expected_fields.items():
            if manifest.get(key) != value: errors.append(f"activation_manifest.{key}:mismatch")
    verification = package.get("verification", {})
    if verification.get("status") != APPROVED: errors.append("verification.status:independent_approval_required")
    _approved_record(verification.get("verification_record"), "verification.verification_record", errors)
    return {"status": "PASS" if not errors else "BLOCKED", "errors": sorted(set(errors)), "secret_values_logged": False, "live_operations_performed": False, "historical_evidence_accepted": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path); parser.add_argument("--expected-commit", required=True); parser.add_argument("--expected-tree", required=True); parser.add_argument("--expected-application-image"); parser.add_argument("--expected-trusted-browser-image"); parser.add_argument("--expected-egress-image"); parser.add_argument("--expected-edge-image"); parser.add_argument("--schema", type=Path); parser.add_argument("--activation-manifest-bytes", type=Path); parser.add_argument("--evidence-verifier-config", type=Path, required=True); parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not _external_verifier_config(args.evidence_verifier_config):
        result = {"status": "BLOCKED", "errors": ["cryptographic_evidence_verifier:unavailable_or_untrusted_configuration"], "secret_values_logged": False}
        if args.json: print(json.dumps(result, sort_keys=True))
        else: print("GATE4_EXTERNAL_CUSTODY=BLOCKED\nERROR=cryptographic_evidence_verifier:unavailable_or_untrusted_configuration")
        return 1
    try: package = json.loads(args.package.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): result = {"status": "BLOCKED", "errors": ["package:unreadable_or_invalid_json"], "secret_values_logged": False}
    else:
        # The config is an onboarding boundary only.  Until an independently
        # authenticated external verifier is integrated, production remains
        # blocked rather than accepting self-attested JSON evidence.
        result = validate(package, expected_commit=args.expected_commit, expected_tree=args.expected_tree, schema_path=args.schema, activation_manifest_path=args.activation_manifest_bytes, expected_application_image=args.expected_application_image, expected_trusted_browser_image=args.expected_trusted_browser_image, expected_egress_image=args.expected_egress_image, expected_edge_image=args.expected_edge_image, require_external_verification=True)
    if args.json: print(json.dumps(result, sort_keys=True))
    else:
        print(f"GATE4_EXTERNAL_CUSTODY={result['status']}")
        for error in result["errors"]: print(f"ERROR={error}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__": sys.exit(main())
