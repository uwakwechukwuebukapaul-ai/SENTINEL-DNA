import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

import {
  buildGate4Evidence,
} from "../../deployment/staging/scripts/generate_gate4_evidence.mjs";

const STAGING_ENV_TEMPLATE = new URL("../../deployment/staging/.env.example", import.meta.url);

const PASSING_VERIFICATION = {
  status: "PASS",
  checks: {
    provider: "PASS",
    runtime: "PASS",
    origin: "PASS",
    browser_contract: "PASS",
    browser_auth: "PASS",
  },
};

test("staging template resolves the adapter to the reviewed provider chain", async () => {
  const template = await readFile(STAGING_ENV_TEMPLATE, "utf8");
  assert.match(template, /^SENTINEL_DNA_TRUSTED_BROWSER_CLIENT=deployment\/staging\/scripts\/trusted_browser_service\/browser-client\.mjs$/m);
  assert.match(template, /^SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT=deployment\/staging\/scripts\/trusted_browser_service\/providers\/playwright-runtime-provider\.mjs$/m);
  assert.doesNotMatch(template, /<approved-provider>|__REPOSITORY_(?:TRUSTED_BROWSER_CLIENT|PROVIDER_BOUNDARY)_MODULE__/);
});

test("Gate 4 evidence is deterministic and records all enforced controls", () => {
  const first = buildGate4Evidence(PASSING_VERIFICATION);
  const second = buildGate4Evidence(PASSING_VERIFICATION);

  assert.deepEqual(first, second);
  assert.equal(first.status, "PASS");
  assert.deepEqual(first.checks, PASSING_VERIFICATION.checks);
  assert.equal(first.controls.provider_module_existence_enforced, true);
  assert.equal(first.controls.provider_export_validation_enforced, true);
  assert.equal(first.controls.runtime_contract_enforced, true);
  assert.equal(first.controls.certified_origin_restriction_enforced, true);
  assert.equal(first.controls.browser_contract_enforced, true);
  assert.equal(first.controls.browser_auth_capability_required, true);
  assert.equal(first.controls.browserAuth_invoked, false);
  assert.doesNotMatch(JSON.stringify(first), /password=|token=|cookie=|authorization=|approved-runtime=/i);
});

test("Gate 4 evidence preserves a safe blocked provider result", () => {
  const evidence = buildGate4Evidence({
    status: "BLOCKED_WITH_REASON",
    failure_category: "TB_PROVIDER_MODULE_MISSING",
    checks: {
      provider: "FAIL",
      runtime: "NOT_RUN",
      origin: "NOT_RUN",
      browser_contract: "NOT_RUN",
      browser_auth: "NOT_RUN",
    },
  });

  assert.equal(evidence.status, "BLOCKED_WITH_REASON");
  assert.equal(evidence.failure_category, "TB_PROVIDER_MODULE_MISSING");
  assert.equal(evidence.controls.browserAuth_invoked, false);
});
