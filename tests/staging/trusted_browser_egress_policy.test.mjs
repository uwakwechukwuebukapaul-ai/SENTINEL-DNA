import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";

import { authorizeConnection, loadEgressPolicy, validateDestination, validateEgressPolicy } from "../../deployment/staging/scripts/trusted_browser_service/policy/egress-policy.mjs";
import { createEgressGateway } from "../../deployment/staging/egress_gateway/gateway-server.mjs";

const POLICY_VALUE = {
  schema: "sentinel-dna-egress-policy-v1",
  schemes: ["https"],
  ports: [443],
  destinations: [{ hostname: "approved.example", ports: [443] }],
};
const bytes = Buffer.from(JSON.stringify(POLICY_VALUE));
const digest = `sha256:${createHash("sha256").update(bytes).digest("hex")}`;

test("policy accepts only injected approved HTTPS destinations", () => {
  const policy = validateEgressPolicy(POLICY_VALUE);
  assert.equal(validateDestination("https://approved.example/", policy).hostname, "approved.example");
  for (const url of [
    "http://approved.example/", "https://unauthorized.example/", "https://127.0.0.1/",
    "https://[::1]/", "https://approved.example:8443/", "https://user:pass@approved.example/",
  ]) assert.throws(() => validateDestination(url, policy), /TB_DESTINATION_REJECTED/);
});

test("network policy rejects IPv4 documentation ranges", async () => {
  const policy = validateEgressPolicy(POLICY_VALUE);
  for (const address of ["192.0.2.1", "198.51.100.1", "203.0.113.1"]) {
    await assert.rejects(
      () => authorizeConnection({
        url: "https://approved.example/",
        policy,
        lookup: async () => [{ address, family: 4 }],
      }),
      /TB_NETWORK_TARGET_REJECTED/,
    );
  }
});

test("network policy rejects IPv6 documentation ranges", async () => {
  const policy = validateEgressPolicy(POLICY_VALUE);
  for (const address of ["2001:db8::1", "2001:0db8::1"]) {
    await assert.rejects(
      () => authorizeConnection({
        url: "https://approved.example/",
        policy,
        lookup: async () => [{ address, family: 6 }],
      }),
      /TB_NETWORK_TARGET_REJECTED/,
    );
  }
});

test("policy loading fails closed for missing, malformed, and tampered policy", async () => {
  await assert.rejects(() => loadEgressPolicy({ env: {} }), { code: "TB_EGRESS_POLICY_UNAVAILABLE" });
  const directory = await mkdtemp(join(tmpdir(), "sentinel-gate4-policy-"));
  const path = join(directory, "policy.json");
  await writeFile(path, bytes);
  await assert.rejects(() => loadEgressPolicy({ env: { SENTINEL_DNA_EGRESS_POLICY_FILE: path, SENTINEL_DNA_EGRESS_POLICY_DIGEST: `sha256:${"0".repeat(64)}` } }), { code: "TB_EGRESS_POLICY_DIGEST_MISMATCH" });
  await writeFile(path, "not-json");
  await assert.rejects(() => loadEgressPolicy({ env: { SENTINEL_DNA_EGRESS_POLICY_FILE: path, SENTINEL_DNA_EGRESS_POLICY_DIGEST: `sha256:${createHash("sha256").update("not-json").digest("hex")}` } }), { code: "TB_EGRESS_POLICY_INVALID" });
});

test("gateway authorization resolves at the gateway and rejects DNS rebinding/TOCTOU", async () => {
  let calls = 0;
  const lookup = async () => {
    calls += 1;
    return [{ address: calls === 1 ? "8.8.8.8" : "8.8.8.8", family: 4 }];
  };
  const first = await authorizeConnection({ url: "https://approved.example/", policy: validateEgressPolicy(POLICY_VALUE), lookup });
  assert.deepEqual(first.addresses, ["8.8.8.8"]);
  await assert.rejects(
    () => authorizeConnection({ url: "https://approved.example/", policy: validateEgressPolicy(POLICY_VALUE), lookup: async () => [{ address: "10.0.0.1", family: 4 }], previousAddresses: first.addresses }),
    /TB_NETWORK_TARGET_REJECTED/,
  );
  await assert.rejects(
    () => {
      let rebindingCalls = 0;
      return authorizeConnection({
        url: "https://approved.example/",
        policy: validateEgressPolicy(POLICY_VALUE),
        lookup: async () => [{ address: rebindingCalls++ === 0 ? "8.8.8.8" : "198.51.100.20", family: 4 }],
        previousAddresses: first.addresses,
      });
    },
    /TB_NETWORK_TOCTOU_REJECTED/,
  );
});

test("gateway fails closed until policy is loaded and on digest change", async () => {
  let digestValue = digest;
  const gateway = createEgressGateway({ policyLoader: async () => ({ policy: validateEgressPolicy(POLICY_VALUE), digest: digestValue }) });
  await assert.rejects(() => gateway.authorize("https://approved.example/"), { code: "TB_EGRESS_GATEWAY_NOT_READY" });
  assert.deepEqual(await gateway.initialize(), { status: "ready", policyDigest: digest });
  digestValue = `sha256:${"a".repeat(64)}`;
  await assert.rejects(() => gateway.authorize("https://approved.example/"), { code: "TB_EGRESS_POLICY_CHANGED" });
  gateway.server.close();
});

test("compose source topology keeps browser on control plus internal egress and gateway on injected uplink", async () => {
  const compose = await readFile(new URL("../../deployment/staging/docker-compose.yml", import.meta.url), "utf8");
  assert.match(compose, /trusted-browser:\s*[\s\S]*trusted_browser_control[\s\S]*trusted_browser_egress/);
  assert.match(compose, /egress-gateway:/);
  assert.match(compose, /egress-gateway:[\s\S]*user:\s*["']10001:10001["']/);
  assert.match(compose, /SENTINEL_DNA_STAGING_APP_IMAGE:\?set immutable staging app image/);
  assert.match(compose, /SENTINEL_DNA_STAGING_EDGE_IMAGE:\?set immutable staging edge image/);
  assert.match(compose, /SENTINEL_DNA_POSTGRES_IMAGE:\?set immutable postgres image/);
  assert.match(compose, /SENTINEL_DNA_REDIS_IMAGE:\?set immutable redis image/);
  assert.match(compose, /trusted_browser_egress:\s*\n\s*internal: true/);
  assert.match(compose, /trusted_browser_gateway_uplink:/);
  assert.doesNotMatch(compose, /trusted-browser:[\s\S]*network_mode:\s*["']host/);
});
