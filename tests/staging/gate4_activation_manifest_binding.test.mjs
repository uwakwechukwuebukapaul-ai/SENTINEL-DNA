import test from "node:test";
import assert from "node:assert/strict";
import {
  computeManifestHash,
  validateReleaseBoundActivationManifest,
} from "../../deployment/staging/scripts/trusted_browser_activation_manifest.mjs";

// Historical synthetic activation fixture. Current release authorization is
// manifest-driven and covered by the signed release-manifest tests.
const HISTORICAL_RELEASE_COMMIT = "8cf91fe0736f5da4521687272ffb10d1dfa0779b";
const HISTORICAL_RELEASE_TREE = "6cf6b210d8a052da92e4b76feafe14247ce1d8bf";
const RELEASE_COMMIT = HISTORICAL_RELEASE_COMMIT;
const RELEASE_TREE = HISTORICAL_RELEASE_TREE;
const digest = (letter) => `sha256:${letter.repeat(64)}`;

function manifest() {
  const value = {
    schema_version: "1.0",
    provider_identity: "provider:test-only",
    runtime_module_identity: "runtime:test-only",
    approved_runtime_module_digest: digest("a"),
    approved_image_runtime_digest: digest("b"),
    staging_origin: "https://synthetic-gate4.example.test",
    activation_timestamp: "2026-09-06T00:00:00Z",
    operator_approval_reference: "approval:test-only",
    approved_runtime_dependency_lockfile_digest: digest("c"),
    approved_browser_auth_bridge_identity: "bridge:test-only",
    approved_browser_auth_bridge_digest: digest("d"),
    release_commit: RELEASE_COMMIT,
    release_tree: RELEASE_TREE,
    application_image_digest: digest("e"),
    trusted_browser_image_digest: digest("f"),
    egress_gateway_image_digest: digest("1"),
    edge_image_digest: digest("2"),
    postgres_image_digest: digest("3"),
    redis_image_digest: digest("4"),
    approved_browser_executable_digest: digest("5"),
    approved_browser_revision: "synthetic-revision",
    approved_browser_version: "synthetic-version",
    approved_browser_base_image_digest: digest("6"),
    approved_egress_policy_reference: "policy:test-only",
    approved_egress_policy_digest: digest("7"),
    egress_gateway_artifact_class: "EXTERNAL_SECURITY_BOUNDARY",
    edge_artifact_class: "EXTERNAL_SECURITY_BOUNDARY",
    approved_edge_configuration_digest: digest("8"),
    approved_edge_tls_custody_reference: "tls-custody:test-only",
    approved_edge_tls_certificate_digest: digest("9"),
    approved_edge_tls_private_key_custody_reference: "tls-key-custody:test-only",
    approved_edge_tls_certificate_key_match_evidence_digest: digest("a"),
    release_approval_reference: "release-approval:test-only",
    registry_identity: "registry.example.test",
    signature_evidence_status: "INDEPENDENTLY_APPROVED",
    attestation_evidence_status: "INDEPENDENTLY_APPROVED",
    sbom_evidence_status: "INDEPENDENTLY_APPROVED",
    signature: {
      scheme: "detached-external",
      key_reference: "key:test-only",
      signature_reference: "signature:test-only",
    },
  };
  value.integrity = { algorithm: "sha256", manifest_hash: computeManifestHash(value) };
  return value;
}

test("strict activation manifest accepts exact release binding", () => {
  const value = validateReleaseBoundActivationManifest(manifest(), {
    releaseCommit: RELEASE_COMMIT,
    releaseTree: RELEASE_TREE,
    certifiedOrigin: "https://synthetic-gate4.example.test",
  });
  assert.equal(value.release_commit, RELEASE_COMMIT);
  assert.equal(value.release_tree, RELEASE_TREE);
});

test("strict activation manifest rejects a wrong release commit", () => {
  const value = manifest();
  value.release_commit = "a".repeat(40);
  value.integrity.manifest_hash = computeManifestHash(value);
  assert.throws(
    () => validateReleaseBoundActivationManifest(value, {
      releaseCommit: RELEASE_COMMIT,
      releaseTree: RELEASE_TREE,
      certifiedOrigin: "https://synthetic-gate4.example.test",
    }),
    (error) => error.code === "TB_RELEASE_IDENTITY_INVALID",
  );
});

test("strict activation manifest rejects missing required image digest", () => {
  const value = manifest();
  delete value.egress_gateway_image_digest;
  value.integrity.manifest_hash = computeManifestHash(value);
  assert.throws(
    () => validateReleaseBoundActivationManifest(value, {
      releaseCommit: RELEASE_COMMIT,
      releaseTree: RELEASE_TREE,
      certifiedOrigin: "https://synthetic-gate4.example.test",
    }),
    (error) => error.code === "TB_PROVIDER_MANIFEST_INVALID",
  );
});

test("strict activation manifest rejects missing external signature", () => {
  const value = manifest();
  delete value.signature;
  value.integrity.manifest_hash = computeManifestHash(value);
  assert.throws(
    () => validateReleaseBoundActivationManifest(value, {
      releaseCommit: RELEASE_COMMIT,
      releaseTree: RELEASE_TREE,
      certifiedOrigin: "https://synthetic-gate4.example.test",
    }),
    (error) => error.code === "TB_PROVIDER_MANIFEST_SIGNATURE_MISSING",
  );
});

test("strict activation manifest rejects missing TLS key custody binding", () => {
  const value = manifest();
  delete value.approved_edge_tls_private_key_custody_reference;
  value.integrity.manifest_hash = computeManifestHash(value);
  assert.throws(
    () => validateReleaseBoundActivationManifest(value, { releaseCommit: RELEASE_COMMIT, releaseTree: RELEASE_TREE, certifiedOrigin: "https://synthetic-gate4.example.test" }),
    (error) => error.code === "TB_PROVIDER_MANIFEST_INVALID",
  );
});
