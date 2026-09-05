import test from "node:test";
import assert from "node:assert/strict";
import { createHmac, createHash } from "node:crypto";
import { createServer } from "node:http";
import {
  authenticateRequest,
  createReplayGuard,
  createRpcRequestHandler,
  createTrustedBrowserService,
} from "../../deployment/staging/trusted_browser_runtime/runtime-service.mjs";
import { createRpcBrowser } from "../../deployment/staging/trusted_browser_runtime/rpc-client.mjs";
import { canonicalJson } from "../../deployment/staging/trusted_browser_runtime/rpc-client.mjs";

const ORIGIN = "https://approved-origin.example";
const CONTEXT = {
  tenantId: "tenant-a",
  subjectId: "analyst-a",
  sessionId: "session-a",
  authorizationContext: "analyst",
  correlationId: "request-a",
};

function signedHeaders(body, key, now) {
  const bytes = Buffer.from(canonicalJson(body));
  const timestamp = String(now);
  const requestId = "rpc-request-a";
  const digest = createHash("sha256").update(bytes).digest("hex");
  const signature = createHmac("sha256", key).update(`${timestamp}.${requestId}.${digest}`).digest("hex");
  return { "x-sentinel-timestamp": timestamp, "x-sentinel-request-id": requestId, "x-sentinel-signature": signature };
}

test("RPC authentication rejects absent or invalid service credentials", () => {
  const body = { operation: "health" };
  assert.throws(() => authenticateRequest({ headers: {}, bodyBytes: Buffer.from(JSON.stringify(body)), serviceKey: "x" }), { code: "TB_SERVICE_AUTH_UNAVAILABLE" });
  const now = Date.now();
  const headers = signedHeaders(body, "a".repeat(32), now);
  assert.doesNotThrow(() => authenticateRequest({ headers, bodyBytes: Buffer.from(JSON.stringify(body)), serviceKey: "a".repeat(32), now }));
  assert.throws(() => authenticateRequest({ headers: { ...headers, "x-sentinel-signature": "0".repeat(64) }, bodyBytes: Buffer.from(JSON.stringify(body)), serviceKey: "a".repeat(32), now }), { code: "TB_SERVICE_AUTH_INVALID" });
});

test("HMAC authenticates canonical content independent of object insertion order", () => {
  const key = "a".repeat(32);
  const first = { operation: "health", z: 1, a: { y: 2, x: 3 } };
  const second = { a: { x: 3, y: 2 }, z: 1, operation: "health" };
  const bytes = Buffer.from(canonicalJson(second));
  const headers = signedHeaders(first, key, Date.now());
  assert.doesNotThrow(() => authenticateRequest({ headers, bodyBytes: bytes, serviceKey: key, now: Number(headers["x-sentinel-timestamp"]) }));
});

test("replay guard rejects duplicate request IDs and expires only after the window", () => {
  let now = 1000;
  const guard = createReplayGuard({ now: () => now, skewMs: 30 });
  assert.equal(guard.accept("unique-request"), true);
  assert.throws(() => guard.accept("unique-request"), { code: "TB_SERVICE_AUTH_REPLAY" });
  now = 1031;
  assert.equal(guard.accept("unique-request"), true);
});

test("production service rejects test-injected runtime factories", () => {
  assert.throws(() => createTrustedBrowserService({ runtimeSetup: async () => ({}), testOnly: false }), { code: "TB_TEST_DEPENDENCY_REJECTED" });
});

function testRuntime(tabOverrides = {}) {
  const locator = {
    async isVisible() { return true; },
    async innerText() { return "safe text"; },
    async getAttribute() { return "safe"; },
    async click() { return undefined; },
  };
  const tab = {
    async goto(url) { return url; },
    async close() {},
    playwright: {
      async getTitle() { return "safe title"; },
      async getVisibleText() { return "safe visible text"; },
      async requestJson(input) { return { status: 200, body: { path: input.path, method: input.method, csrfRequired: input.csrfRequired } }; },
      locator() { return locator; },
    },
    capabilities: { async get(name) { return name === "browserAuth" ? { async request() { return { status: "submitted" }; } } : undefined; } },
    ...tabOverrides,
  };
  return {
    async setup() {
      return {
        browsers: { async getForUrl() { return { tabs: { async new() { return tab; } }, async close() {} }; } },
        async close() {},
      };
    },
  };
}

test("service boundary binds context and returns only serializable capabilities", async () => {
  const service = createTrustedBrowserService({ runtimeSetup: async () => testRuntime().setup(), testOnly: true, auditSink: async () => {} });
  const created = await service.handle({ operation: "create_session", certifiedOrigin: ORIGIN, securityContext: CONTEXT }, "request-a");
  assert.equal(created.tenantId, "tenant-a");
  assert.equal(typeof created.sessionId, "string");
  assert.equal(Object.getPrototypeOf(created), Object.prototype);
  await assert.rejects(() => service.handle({ operation: "get_title", sessionId: created.sessionId, securityContext: { ...CONTEXT, tenantId: "tenant-b" } }, "request-b"), { code: "TB_TENANT_CONTEXT_MISMATCH" });
  const title = await service.handle({ operation: "get_title", sessionId: created.sessionId, securityContext: CONTEXT }, "request-c");
  assert.deepEqual(title, { value: "safe title" });
  const auth = await service.handle({ operation: "browser_auth", sessionId: created.sessionId, securityContext: CONTEXT, fields: [{ id: "username", label: "Username", type: "text", selector: "#username" }] }, "request-auth");
  assert.deepEqual(auth, { status: "submitted" });
  await assert.rejects(() => service.handle({ operation: "unknown_privileged_operation", sessionId: created.sessionId, securityContext: CONTEXT }, "request-d"), { code: "TB_RPC_OPERATION_UNAUTHORIZED" });
  await assert.rejects(() => service.handle({ operation: "locator_create", selector: "body", password: "secret", securityContext: CONTEXT, sessionId: created.sessionId }, "request-e"), { code: "TB_CREDENTIAL_FIELD_REJECTED" });
  await service.handle({ operation: "close_session", sessionId: created.sessionId, securityContext: CONTEXT }, "request-f");
});

test("BrowserAuth cannot fall back to the incompatible direct tab.browserAuth surface", async () => {
  const service = createTrustedBrowserService({
    runtimeSetup: async () => testRuntime({
      capabilities: undefined,
      browserAuth: { async request() { return { status: "must-not-succeed" }; } },
    }).setup(),
    testOnly: true,
    auditSink: async () => {},
  });
  const created = await service.handle({ operation: "create_session", certifiedOrigin: ORIGIN, securityContext: CONTEXT }, "old-contract-create");
  await assert.rejects(
    () => service.handle({ operation: "browser_auth", sessionId: created.sessionId, securityContext: CONTEXT, fields: [{ id: "username", label: "Username", type: "text", selector: "#username" }] }, "old-contract-auth"),
    { code: "TB_AUTH_CAPABILITY_MISSING" },
  );
});

test("BrowserAuth rejects missing and malformed capabilities", async () => {
  for (const capabilities of [undefined, { get: async () => undefined }, { get: "not-a-function" }]) {
    const service = createTrustedBrowserService({
      runtimeSetup: async () => testRuntime({ capabilities }).setup(),
      testOnly: true,
      auditSink: async () => {},
    });
    const created = await service.handle({ operation: "create_session", certifiedOrigin: ORIGIN, securityContext: CONTEXT }, "capability-create");
    await assert.rejects(
      () => service.handle({ operation: "browser_auth", sessionId: created.sessionId, securityContext: CONTEXT, fields: [{ id: "username", label: "Username", type: "text", selector: "#username" }] }, "capability-auth"),
      { code: "TB_AUTH_CAPABILITY_MISSING" },
    );
  }
});

test("session security identity binding rejects changed runtime identity", async () => {
  const service = createTrustedBrowserService({ runtimeSetup: async () => testRuntime().setup(), securityIdentity: { binding: "identity-a" }, testOnly: true, auditSink: async () => {} });
  const created = await service.handle({ operation: "create_session", certifiedOrigin: ORIGIN, securityContext: CONTEXT }, "identity-create");
  await assert.rejects(() => service.handle({ operation: "get_title", sessionId: created.sessionId, identityBinding: "identity-b", securityContext: CONTEXT }, "identity-mismatch"), { code: "TB_SECURITY_IDENTITY_MISMATCH" });
  const title = await service.handle({ operation: "get_title", sessionId: created.sessionId, identityBinding: "identity-a", securityContext: CONTEXT }, "identity-match");
  assert.equal(title.value, "safe title");
  await service.handle({ operation: "close_session", sessionId: created.sessionId, identityBinding: "identity-a", securityContext: CONTEXT }, "identity-close");
});

test("service rejects missing tenant context and malformed certified origin", async () => {
  const service = createTrustedBrowserService({ runtimeSetup: async () => testRuntime().setup(), testOnly: true, auditSink: async () => {} });
  await assert.rejects(() => service.handle({ operation: "create_session", certifiedOrigin: ORIGIN }, "request-g"), { code: "TB_TENANT_CONTEXT_INVALID" });
  await assert.rejects(() => service.handle({ operation: "create_session", certifiedOrigin: "http://localhost", securityContext: CONTEXT }, "request-h"), { code: "TB_ORIGIN_REJECTED" });
});

test("request_json is same-origin, method-bound, and CSRF-bound", async () => {
  const service = createTrustedBrowserService({
    runtimeSetup: async () => testRuntime().setup(),
    testOnly: true,
    lookup: async () => [{ address: "93.184.216.34", family: 4 }],
    auditSink: async () => {},
  });
  const created = await service.handle({ operation: "create_session", certifiedOrigin: "https://example.com", securityContext: CONTEXT }, "request-json-create");
  const safe = await service.handle({ operation: "request_json", sessionId: created.sessionId, securityContext: CONTEXT, path: "/api/auth/me", method: "GET", csrfRequired: false }, "request-json-get");
  assert.equal(safe.body.csrfRequired, false);
  await assert.rejects(() => service.handle({ operation: "request_json", sessionId: created.sessionId, securityContext: CONTEXT, path: "/api/write", method: "POST", csrfRequired: false }, "request-json-no-csrf"), { code: "TB_REQUEST_INVALID" });
  await assert.rejects(() => service.handle({ operation: "request_json", sessionId: created.sessionId, securityContext: CONTEXT, path: "https://example.com/escape", method: "GET", csrfRequired: false }, "request-json-absolute"), { code: "TB_REQUEST_INVALID" });
  await service.handle({ operation: "close_session", sessionId: created.sessionId, securityContext: CONTEXT }, "request-json-close");
});

test("audit failure does not leave a usable partial session", async () => {
  let closed = 0;
  const runtime = testRuntime();
  const service = createTrustedBrowserService({
    runtimeSetup: async () => {
      const value = await runtime.setup();
      const original = value.close;
      value.close = async () => { closed += 1; await original(); };
      return value;
    },
    testOnly: true,
    auditSink: async () => { throw new Error("audit sink unavailable"); },
  });
  await assert.rejects(() => service.handle({ operation: "create_session", certifiedOrigin: ORIGIN, securityContext: CONTEXT }, "request-i"), { code: "TB_AUDIT_FAILED" });
  assert.equal(closed, 1);
});

test("application RPC client crosses only JSON and never exposes native browser objects", async () => {
  const previous = { key: process.env.SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_KEY, host: process.env.SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_HOST, port: process.env.SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_PORT };
  process.env.SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_KEY = "a".repeat(32);
  process.env.SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_HOST = "trusted-browser";
  process.env.SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_PORT = "3000";
  const responses = [
    { ok: true, result: { serviceEpoch: "test-epoch", status: "ok" } },
    { ok: true, result: { sessionId: "service-session", tenantId: "tenant-a", origin: ORIGIN } },
    { ok: true, result: { value: 1 } },
    { ok: true, result: { value: true } },
  ];
  const calls = [];
  try {
    const browser = createRpcBrowser({ origin: ORIGIN, tenantContext: CONTEXT, testOnly: true, fetchImpl: async (url, options) => {
      calls.push({ url, body: JSON.parse(Buffer.from(options.body).toString("utf8")), headers: options.headers });
      return { ok: true, status: 200, json: async () => responses.shift() };
    } });
    assert.equal(typeof browser.newContext, "undefined");
    const tab = await browser.tabs.new();
    assert.equal(typeof tab.playwright.evaluate, "undefined");
    assert.equal(typeof tab.playwright.locator, "function");
    const locator = tab.playwright.locator("#safe");
    assert.equal(await locator.count(), 1);
    assert.equal(await locator.isVisible(), true);
    assert.equal(calls.find((call) => call.body.operation === "create_session").body.operation, "create_session");
    assert.equal(calls[0].body.securityContext.tenantId, "tenant-a");
    assert.match(calls[0].headers["x-sentinel-signature"], /^[a-f0-9]{64}$/);
  } finally {
    for (const [name, value] of Object.entries({ SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_KEY: previous.key, SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_HOST: previous.host, SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_PORT: previous.port })) {
      if (value === undefined) delete process.env[name]; else process.env[name] = value;
    }
  }
});

test("RPC client and HTTP service complete an authenticated end-to-end operation", async () => {
  const key = "b".repeat(32);
  const service = createTrustedBrowserService({ runtimeSetup: async () => testRuntime().setup(), testOnly: true, auditSink: async () => {} });
  const server = createServer(createRpcRequestHandler({ service, serviceKey: key }));
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  try {
    const browser = createRpcBrowser({ origin: ORIGIN, tenantContext: CONTEXT, testOnly: true, serviceKey: key, endpoint: `http://127.0.0.1:${address.port}/rpc` });
    const tab = await browser.tabs.new();
    assert.equal(await tab.playwright.getTitle(), "safe title");
    await tab.close();

    const body = JSON.stringify({ operation: "health" });
    const headers = signedHeaders(JSON.parse(body), key, Date.now());
    const first = await fetch(`http://127.0.0.1:${address.port}/rpc`, { method: "POST", headers: { ...headers, "content-type": "application/json" }, body });
    assert.equal(first.status, 200);
    const invalid = await fetch(`http://127.0.0.1:${address.port}/rpc`, { method: "POST", headers: { ...headers, "x-sentinel-request-id": "rpc-invalid", "x-sentinel-signature": "0".repeat(64), "content-type": "application/json" }, body });
    assert.equal(invalid.status, 400);
    assert.equal((await invalid.json()).code, "TB_SERVICE_AUTH_INVALID");
    const replay = await fetch(`http://127.0.0.1:${address.port}/rpc`, { method: "POST", headers: { ...headers, "content-type": "application/json" }, body });
    assert.equal(replay.status, 400);
    assert.equal((await replay.json()).code, "TB_SERVICE_AUTH_REPLAY");
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});

test("RPC initialization and operation failures fail closed without a local fallback", async () => {
  for (const failure of [
    Object.assign(new Error("rejected"), { code: "TB_RPC_AUTH_INVALID" }),
    Object.assign(new Error("timeout"), { name: "AbortError" }),
    Object.assign(new Error("offline"), { code: "ECONNREFUSED" }),
  ]) {
    let calls = 0;
    const browser = createRpcBrowser({
      origin: ORIGIN,
      tenantContext: CONTEXT,
      testOnly: true,
      serviceKey: "e".repeat(32),
      endpoint: "http://127.0.0.1:1/rpc",
      fetchImpl: async () => { calls += 1; throw failure; },
    });
    const expectedCode = failure.name === "AbortError" ? "TB_RPC_TIMEOUT" : failure.code?.startsWith("TB_") ? failure.code : "TB_RPC_UNAVAILABLE";
    await assert.rejects(() => browser.tabs.new(), (error) => error.code === expectedCode);
    assert.equal(calls, 1);
  }
});

test("unsafe runtime results are rejected before response serialization", async () => {
  for (const malicious of [
    { password: "hidden" },
    { nested: { token: "hidden" } },
    { locator: { count: () => 1 } },
    new Map([["native", "browser"]]),
  ]) {
    const service = createTrustedBrowserService({
      runtimeSetup: async () => ({
        browsers: { getForUrl: async () => ({ tabs: { new: async () => ({ goto: async () => {}, close: async () => {}, playwright: { getTitle: async () => malicious, getVisibleText: async () => "safe", locator: () => ({}) }, browserAuth: { request: async () => ({ status: "submitted" }) } }) } }) },
        close: async () => {},
      }),
      testOnly: true,
      auditSink: async () => {},
    });
    const created = await service.handle({ operation: "create_session", certifiedOrigin: ORIGIN, securityContext: CONTEXT }, "unsafe-result");
    await assert.rejects(
      () => service.handle({ operation: "get_title", sessionId: created.sessionId, securityContext: CONTEXT }, "unsafe-result-2"),
      (error) => typeof error.code === "string" && error.code.startsWith("TB_"),
    );
  }
});
