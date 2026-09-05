import { createHash, createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { createServer } from "node:http";
import { loadActivationManifest } from "../scripts/trusted_browser_activation_manifest.mjs";
import { verifyConfiguredRuntimeDigest } from "../scripts/verify_gate4_external_artifacts.mjs";
import { setupBrowserRuntime as setupProviderRuntime } from "../scripts/trusted_browser_service/providers/playwright-runtime-provider.mjs";
import { parseTrustedOrigin } from "../scripts/trusted_browser_service/policy/origin-policy.mjs";
import { createRuntimePolicy } from "../scripts/trusted_browser_service/policy/runtime-policy.mjs";
import { createTenantContext, assertSameTenantContext } from "../scripts/trusted_browser_service/policy/tenant-context.mjs";
import { assertNoSecretFields } from "../scripts/trusted_browser_service/policy/secret-fields.mjs";
import { canonicalJson } from "./rpc-client.mjs";

export const TRUSTED_BROWSER_SERVICE_ENV = "codex-app";
export const SERVICE_KEY_ENV = "SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_KEY";
export const SERVICE_PORT_ENV = "SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_PORT";
export const SERVICE_HOST_ENV = "SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_HOST";
export const MAX_BODY_BYTES = 64 * 1024;
export const REQUEST_SKEW_MS = 30_000;
export const REPLAY_MODE_ENV = "SENTINEL_DNA_TRUSTED_BROWSER_REPLAY_MODE";
export const REPLICA_COUNT_ENV = "SENTINEL_DNA_TRUSTED_BROWSER_REPLICA_COUNT";

const SAFE_OPERATIONS = new Set([
  "health",
  "create_session",
  "navigate",
  "get_title",
  "get_visible_text",
  "request_json",
  "locator_create",
  "locator_count",
  "locator_is_visible",
  "locator_inner_text",
  "locator_attribute",
  "locator_click",
  "browser_auth",
  "close_session",
]);

function serviceError(code, message = "trusted browser service request rejected") {
  const error = new Error(message);
  error.code = code;
  return error;
}

function safeString(value, code) {
  if (typeof value !== "string" || !value.trim() || value.length > 512) {
    throw serviceError(code);
  }
  return value;
}

function jsonBytes(value) {
  return Buffer.from(JSON.stringify(value), "utf8");
}

function digestBody(bytes) {
  let value;
  try { value = JSON.parse(bytes.toString("utf8")); } catch { throw serviceError("TB_RPC_REQUEST_INVALID"); }
  return createHash("sha256").update(canonicalJson(value), "utf8").digest("hex");
}

function signaturePayload({ timestamp, requestId, bodyDigest }) {
  return `${timestamp}.${requestId}.${bodyDigest}`;
}

export function authenticateRequest({ headers, bodyBytes, now = Date.now(), serviceKey = process.env?.[SERVICE_KEY_ENV] }) {
  if (typeof serviceKey !== "string" || serviceKey.length < 32) {
    throw serviceError("TB_SERVICE_AUTH_UNAVAILABLE");
  }
  const timestamp = safeString(headers?.["x-sentinel-timestamp"], "TB_SERVICE_AUTH_INVALID");
  const requestId = safeString(headers?.["x-sentinel-request-id"], "TB_SERVICE_AUTH_INVALID");
  const supplied = safeString(headers?.["x-sentinel-signature"], "TB_SERVICE_AUTH_INVALID");
  if (!/^\d+$/.test(timestamp) || !/^[A-Fa-f0-9]{64}$/.test(supplied)) throw serviceError("TB_SERVICE_AUTH_INVALID");
  const timestampMs = Number(timestamp);
  if (!Number.isSafeInteger(timestampMs) || Math.abs(now - timestampMs) > REQUEST_SKEW_MS) {
    throw serviceError("TB_SERVICE_AUTH_EXPIRED");
  }
  const expected = createHmac("sha256", serviceKey)
    .update(signaturePayload({ timestamp, requestId, bodyDigest: digestBody(bodyBytes) }), "utf8")
    .digest("hex");
  const left = Buffer.from(supplied, "hex");
  const right = Buffer.from(expected, "hex");
  if (left.length !== right.length || !timingSafeEqual(left, right)) {
    throw serviceError("TB_SERVICE_AUTH_INVALID");
  }
  return Object.freeze({ requestId, timestamp: timestampMs });
}

export function createReplayGuard({ now = () => Date.now(), skewMs = REQUEST_SKEW_MS } = {}) {
  const seen = new Map();
  return Object.freeze({
    accept(requestId) {
      const current = now();
      for (const [id, seenAt] of seen) if (seenAt <= current - skewMs) seen.delete(id);
      if (seen.has(requestId)) throw serviceError("TB_SERVICE_AUTH_REPLAY");
      seen.set(requestId, current);
      return true;
    },
  });
}

function contextFromRequest(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw serviceError("TB_TENANT_CONTEXT_INVALID");
  }
  try { return createTenantContext(value); } catch { throw serviceError("TB_TENANT_CONTEXT_INVALID"); }
}

function assertRequestShape(request) {
  if (!request || typeof request !== "object" || Array.isArray(request)) {
    throw serviceError("TB_RPC_REQUEST_INVALID");
  }
  const untrustedPayload = { ...request };
  delete untrustedPayload.securityContext;
  delete untrustedPayload.sessionId;
  try { assertNoSecretFields(untrustedPayload); } catch { throw serviceError("TB_CREDENTIAL_FIELD_REJECTED"); }
  const operation = safeString(request.operation, "TB_RPC_OPERATION_INVALID");
  if (!SAFE_OPERATIONS.has(operation)) throw serviceError("TB_RPC_OPERATION_UNAUTHORIZED");
  return operation;
}

function publicResult(value, seen = new WeakSet()) {
  if (value === null || typeof value === "string" || typeof value === "boolean") return value;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw serviceError("TB_RPC_RESULT_INVALID");
    return value;
  }
  if (!value || typeof value !== "object" || Object.getPrototypeOf(value) !== Object.prototype && Object.getPrototypeOf(value) !== null) throw serviceError("TB_RPC_RESULT_INVALID");
  if (seen.has(value)) throw serviceError("TB_RPC_RESULT_INVALID");
  seen.add(value);
  const result = {};
  for (const [key, child] of Object.entries(value)) {
    if (isSecretResultKey(key)) throw serviceError("TB_CREDENTIAL_FIELD_REJECTED");
    result[key] = publicResult(child, seen);
  }
  seen.delete(value);
  return result;
}

function isSecretResultKey(key) {
  try { assertNoSecretFields({ [key]: null }); return false; } catch { return true; }
}

function auditRecord({ requestId, operation, context, outcome, code = undefined }) {
  if (!context) throw serviceError("TB_AUDIT_CONTEXT_MISSING");
  const result = {
    requestId,
    operation,
    tenantId: context.tenantId,
    subjectId: context.subjectId,
    sessionId: context.sessionId,
    authorizationContext: context.authorizationContext,
    ...(context.correlationId ? { correlationId: context.correlationId } : {}),
    outcome,
    ...(code ? { code } : {}),
  };
  return Object.freeze(result);
}

function opaqueId(prefix) {
  return `${prefix}_${randomBytes(18).toString("hex")}`;
}

async function closeResource(resource, operation) {
  if (!resource || typeof resource.close !== "function") return;
  try {
    await resource.close();
  } catch {
    throw serviceError("TB_LIFECYCLE_CLEANUP_FAILED", operation);
  }
}

export function createTrustedBrowserService({
  runtimeSetup = undefined,
  auditSink = (event) => process.stdout.write(`${JSON.stringify(event)}\n`),
  testOnly = false,
  now = () => Date.now(),
  securityIdentity = undefined,
  lookup = undefined,
  serviceEpoch = "test-epoch",
} = {}) {
  if (runtimeSetup && !testOnly) throw serviceError("TB_TEST_DEPENDENCY_REJECTED");
  if (typeof auditSink !== "function") throw serviceError("TB_AUDIT_UNAVAILABLE");
  if (!testOnly && (!securityIdentity || typeof securityIdentity.binding !== "string" || typeof serviceEpoch !== "string")) throw serviceError("TB_SECURITY_IDENTITY_UNAVAILABLE");
  const sessions = new Map();

  async function emitAudit(args) {
    const event = auditRecord(args);
    try {
      await auditSink(event);
    } catch {
      throw serviceError("TB_AUDIT_FAILED");
    }
  }

  async function setupSession(request, requestId) {
    const context = contextFromRequest(request.securityContext);
    const certifiedOrigin = safeString(request.certifiedOrigin, "TB_ORIGIN_REJECTED");
    let origin;
    try { origin = parseTrustedOrigin(certifiedOrigin, { certifiedOrigin }).origin; } catch { throw serviceError("TB_ORIGIN_REJECTED"); }
    const policy = createRuntimePolicy({ certifiedOrigin: origin, tenantContext: context, production: true, lookup });
    const setup = runtimeSetup || ((options) => setupProviderRuntime(options));
    const runtime = await setup({ environment: TRUSTED_BROWSER_SERVICE_ENV, certifiedOrigin: origin, tenantContext: context, securityMode: "trusted-rpc" });
    const browser = await runtime.browsers.getForUrl(origin);
    const tab = await browser.tabs.new();
    const sessionId = opaqueId("s");
    sessions.set(sessionId, { runtime, browser, tab, context, policy, origin, closed: false, identityBinding: securityIdentity?.binding });
    try {
      await emitAudit({ requestId, operation: "create_session", context, outcome: "success" });
    } catch (error) {
      sessions.delete(sessionId);
      for (const [resource, operation] of [[tab, "tab.close"], [browser, "browser.close"], [runtime, "runtime.close"]]) {
        try { await closeResource(resource, operation); } catch { /* preserve the primary audit failure */ }
      }
      throw error;
    }
    return { sessionId, tenantId: context.tenantId, origin, serviceEpoch, ...(securityIdentity?.binding ? { identityBinding: securityIdentity.binding } : {}) };
  }

  function getSession(request) {
    const session = sessions.get(safeString(request.sessionId, "TB_SESSION_INVALID"));
    if (!session || session.closed) throw serviceError("TB_SESSION_INVALID");
    if (!testOnly && request.serviceEpoch !== serviceEpoch) throw serviceError("TB_SERVICE_EPOCH_MISMATCH");
    const context = contextFromRequest(request.securityContext);
    if (session.identityBinding && request.identityBinding !== session.identityBinding) throw serviceError("TB_SECURITY_IDENTITY_MISMATCH");
    try { assertSameTenantContext(session.context, context); } catch { throw serviceError("TB_TENANT_CONTEXT_MISMATCH"); }
    session.policy.bindTenant(context);
    return { session, context };
  }

  async function closeSession(request, requestId) {
    const { session, context } = getSession(request);
    session.closed = true;
    sessions.delete(request.sessionId);
    let failure;
    for (const [resource, operation] of [[session.tab, "tab.close"], [session.browser, "browser.close"], [session.runtime, "runtime.close"]]) {
      try { await closeResource(resource, operation); } catch (error) { failure ||= error; }
    }
    await emitAudit({ requestId, operation: "close_session", context, outcome: failure ? "failure" : "success", code: failure?.code });
    if (failure) throw failure;
    return { closed: true };
  }

  async function handle(request, requestId) {
    const operation = assertRequestShape(request);
    if (operation === "health") return { status: "ok", environment: TRUSTED_BROWSER_SERVICE_ENV, serviceEpoch };
    if (operation === "create_session") return setupSession(request, requestId);
    if (operation === "close_session") return closeSession(request, requestId);
    const { session, context } = getSession(request);
    let result;
    if (operation === "navigate") {
      const url = await session.policy.validateNavigation(safeString(request.url, "TB_NAVIGATION_REJECTED"));
      result = { url: await session.tab.goto(url) };
    } else if (operation === "get_title") {
      result = { value: await session.tab.playwright.getTitle() };
    } else if (operation === "get_visible_text") {
      result = { value: await session.tab.playwright.getVisibleText() };
    } else if (operation === "request_json") {
      const path = safeString(request.path, "TB_REQUEST_INVALID");
      const method = request.method || "GET";
      if (!path.startsWith("/") || path.startsWith("//") || !["GET", "POST"].includes(method) || request.csrfRequired !== (method === "POST")) throw serviceError("TB_REQUEST_INVALID");
      await session.policy.validateNavigation(path);
      assertNoSecretFields(request.body);
      result = await session.tab.playwright.requestJson({ path, method, body: request.body, csrfRequired: method === "POST" });
    } else if (operation === "locator_create") {
      const selector = safeString(request.selector, "TB_LOCATOR_INVALID");
      result = { locatorId: opaqueId("l"), selector };
      session.locators ||= new Map();
      session.locators.set(result.locatorId, session.tab.playwright.locator(selector));
    } else {
      const locator = request.selector
        ? session.tab.playwright.locator(safeString(request.selector, "TB_LOCATOR_INVALID"))
        : session.locators?.get(safeString(request.locatorId, "TB_LOCATOR_INVALID"));
      if (!locator) throw serviceError("TB_LOCATOR_INVALID");
      if (operation === "locator_count") result = { value: await locator.count() };
      else if (operation === "locator_is_visible") result = { value: await locator.isVisible() };
      else if (operation === "locator_inner_text") result = { value: await locator.innerText() };
      else if (operation === "locator_attribute") result = { value: await locator.getAttribute(safeString(request.attribute, "TB_ATTRIBUTE_INVALID")) };
      else if (operation === "locator_click") result = { value: await locator.click() };
      else if (operation === "browser_auth") {
        if (!session.tab.browserAuth || typeof session.tab.browserAuth.request !== "function") throw serviceError("TB_AUTH_CAPABILITY_MISSING");
        result = await session.tab.browserAuth.request({ securityContext: context, request: { origin: session.origin, fields: request.fields, ...(request.submit ? { submit: request.submit } : {}) } });
      }
    }
    result = publicResult(result);
    await emitAudit({ requestId, operation, context, outcome: "success" });
    return result;
  }

  return Object.freeze({
    handle,
    async closeAll() {
      let failure;
      for (const sessionId of [...sessions.keys()]) {
        try { await closeSession({ sessionId, securityContext: sessions.get(sessionId).context }, opaqueId("cleanup")); } catch (error) { failure ||= error; }
      }
      if (failure) throw failure;
    },
  });
}

async function readJsonBody(request) {
  const chunks = [];
  let length = 0;
  for await (const chunk of request) {
    length += chunk.length;
    if (length > MAX_BODY_BYTES) throw serviceError("TB_RPC_REQUEST_TOO_LARGE");
    chunks.push(chunk);
  }
  const bytes = Buffer.concat(chunks);
  try { return { bytes, value: JSON.parse(bytes.toString("utf8")) }; } catch { throw serviceError("TB_RPC_REQUEST_INVALID"); }
}

export async function assertProductionConfiguration() {
  const required = [SERVICE_KEY_ENV, SERVICE_HOST_ENV, SERVICE_PORT_ENV, "SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME", "SENTINEL_DNA_APPROVED_RUNTIME_DIGEST", "SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST", "SENTINEL_DNA_IMAGE_DIGEST", "SENTINEL_DNA_EGRESS_POLICY_REFERENCE", REPLAY_MODE_ENV, REPLICA_COUNT_ENV];
  for (const name of required) if (typeof process.env?.[name] !== "string" || !process.env[name].trim()) throw serviceError("TB_STARTUP_CONFIGURATION_INVALID");
  if (process.env[REPLAY_MODE_ENV] !== "single-instance" || process.env[REPLICA_COUNT_ENV] !== "1") throw serviceError("TB_REPLAY_CONFIGURATION_INVALID");
  const manifest = await loadActivationManifest();
  if (manifest.approved_image_runtime_digest.toLowerCase() !== process.env.SENTINEL_DNA_IMAGE_DIGEST.toLowerCase()) throw serviceError("TB_IMAGE_IDENTITY_INVALID");
  const runtime = await verifyConfiguredRuntimeDigest(manifest, { requireOperatorDigest: true, requireDependencyClosure: true });
  if (runtime.status !== "PASS") throw serviceError(runtime.code || "TB_RUNTIME_UNAVAILABLE");
  if (process.env.SENTINEL_DNA_TRUSTED_BROWSER_EGRESS_READY !== "true") throw serviceError("TB_EGRESS_POLICY_UNAVAILABLE");
  const binding = createHash("sha256").update(canonicalJson({
    runtime: process.env.SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME,
    runtimeDigest: process.env.SENTINEL_DNA_APPROVED_RUNTIME_DIGEST,
    imageDigest: process.env.SENTINEL_DNA_IMAGE_DIGEST,
    manifest: process.env.SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST,
    egress: process.env.SENTINEL_DNA_EGRESS_POLICY_REFERENCE,
  }), "utf8").digest("hex");
  return Object.freeze({ binding });
}

export async function startTrustedBrowserService() {
  const securityIdentity = await assertProductionConfiguration();
  const serviceEpoch = randomBytes(18).toString("hex");
  const service = createTrustedBrowserService({ securityIdentity, serviceEpoch });
  const host = process.env[SERVICE_HOST_ENV];
  const port = Number(process.env[SERVICE_PORT_ENV]);
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw serviceError("TB_STARTUP_CONFIGURATION_INVALID");
  const server = createServer(createRpcRequestHandler({ service }));
  await new Promise((resolve, reject) => { server.once("error", reject); server.listen(port, host, resolve); });
  return Object.freeze({ server, service });
}

export function createRpcRequestHandler({ service, serviceKey = process.env?.[SERVICE_KEY_ENV], replayGuard = createReplayGuard() } = {}) {
  if (!service || typeof service.handle !== "function") throw serviceError("TB_RPC_CONFIGURATION_INVALID");
  return async (request, response) => {
    try {
      if (request.method === "GET" && request.url === "/healthz") {
        response.writeHead(200, { "content-type": "application/json" });
        response.end(JSON.stringify({ ok: true, status: "ready" }));
        return;
      }
      if (request.method !== "POST" || request.url !== "/rpc") throw serviceError("TB_RPC_ROUTE_INVALID");
      const { bytes, value } = await readJsonBody(request);
      const auth = authenticateRequest({ headers: request.headers, bodyBytes: bytes, serviceKey });
      replayGuard.accept(auth.requestId);
      const result = await service.handle(value, auth.requestId);
      response.writeHead(200, { "content-type": "application/json" });
      response.end(JSON.stringify({ ok: true, result: publicResult(result) }));
    } catch (error) {
      response.writeHead(400, { "content-type": "application/json" });
      response.end(JSON.stringify({ ok: false, code: error?.code || "TB_RPC_FAILED" }));
    }
  };
}

if (process.argv[1] && process.argv[1].endsWith("runtime-service.mjs")) {
  startTrustedBrowserService().catch((error) => {
    process.stderr.write(`${error.code || "TB_STARTUP_FAILED"}\n`);
    process.exitCode = 1;
  });
}
