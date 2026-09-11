import { createHash, createHmac, randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";

import { configuredCertifiedOrigin, parseTrustedOrigin, parseTrustedNavigation } from "../scripts/trusted_browser_service/policy/origin-policy.mjs";
import { createTenantContext } from "../scripts/trusted_browser_service/policy/tenant-context.mjs";
import { assertNoSecretFields } from "../scripts/trusted_browser_service/policy/secret-fields.mjs";

export const SERVICE_KEY_ENV = "SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_KEY";
export const SERVICE_HOST_ENV = "SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_HOST";
export const SERVICE_PORT_ENV = "SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_PORT";
export const REQUEST_TIMEOUT_MS = 30_000;

function configuredServiceKey() {
  const direct = process.env?.[SERVICE_KEY_ENV];
  const file = process.env?.[`${SERVICE_KEY_ENV}_FILE`];
  if (direct && file) throw rpcError("TB_RPC_CONFIGURATION_AMBIGUOUS");
  if (file) {
    try { return readFileSync(file, "utf8").trim(); } catch { throw rpcError("TB_RPC_CONFIGURATION_INVALID"); }
  }
  return direct;
}

export function canonicalize(value) {
  if (value === null || typeof value === "string" || typeof value === "boolean") return value;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonicalize(value[key])]));
  }
  throw rpcError("TB_RPC_REQUEST_INVALID");
}

export function canonicalJson(value) { return JSON.stringify(canonicalize(value)); }

function rpcError(code) { const error = new Error(`[${code}] trusted browser RPC failed`); error.code = code; return error; }

function configuration({ serviceKey = undefined, endpoint = undefined, testOnly = false } = {}) {
  if ((serviceKey !== undefined || endpoint !== undefined) && testOnly !== true) throw rpcError("TB_TEST_DEPENDENCY_REJECTED");
  if (serviceKey !== undefined || endpoint !== undefined) {
    if (typeof serviceKey !== "string" || serviceKey.length < 32 || typeof endpoint !== "string" || !endpoint.startsWith("http://127.0.0.1:")) throw rpcError("TB_RPC_CONFIGURATION_INVALID");
    return Object.freeze({ key: serviceKey, endpoint });
  }
  const key = configuredServiceKey();
  const host = process.env?.[SERVICE_HOST_ENV];
  const port = process.env?.[SERVICE_PORT_ENV];
  if (typeof key !== "string" || key.length < 32 || typeof host !== "string" || !host.trim() || !/^\d+$/.test(String(port))) throw rpcError("TB_RPC_CONFIGURATION_INVALID");
  const numberPort = Number(port);
  if (!Number.isInteger(numberPort) || numberPort < 1 || numberPort > 65535 || /[/:?#]/.test(host)) throw rpcError("TB_RPC_CONFIGURATION_INVALID");
  return Object.freeze({ key, endpoint: `http://${host}:${numberPort}/rpc` });
}

function bodyBytes(value) { return Buffer.from(canonicalJson(value), "utf8"); }
function signedHeaders(bytes, key) {
  const timestamp = String(Date.now());
  const requestId = randomUUID();
  const digest = createHash("sha256").update(bytes).digest("hex");
  const signature = createHmac("sha256", key).update(`${timestamp}.${requestId}.${digest}`, "utf8").digest("hex");
  return { "content-type": "application/json", "x-sentinel-timestamp": timestamp, "x-sentinel-request-id": requestId, "x-sentinel-signature": signature };
}

function safeResult(value) { assertNoSecretFields(value); return value; }

export function createRpcBrowser({ origin = configuredCertifiedOrigin(), tenantContext, fetchImpl = globalThis.fetch, testOnly = false, serviceKey = undefined, endpoint = undefined } = {}) {
  if (fetchImpl !== globalThis.fetch && testOnly !== true) throw rpcError("TB_TEST_DEPENDENCY_REJECTED");
  const config = configuration({ serviceKey, endpoint, testOnly });
  const context = createTenantContext(tenantContext);
  const certifiedOrigin = parseTrustedOrigin(origin, { certifiedOrigin: origin }).origin;
  if (typeof fetchImpl !== "function") throw rpcError("TB_RPC_UNAVAILABLE");
  const sessions = new Map();
  let serviceEpoch;

  async function send(operation, fields = {}, sessionId = undefined, includeEpoch = true) {
    const request = { operation, ...fields, ...(sessionId ? { sessionId } : {}), ...(includeEpoch && serviceEpoch ? { serviceEpoch } : {}), ...(sessionId && sessions.get(sessionId) ? { identityBinding: sessions.get(sessionId) } : {}), securityContext: context };
    assertNoSecretFields({ operation, ...fields });
    const bytes = bodyBytes(request);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      const response = await fetchImpl(config.endpoint, { method: "POST", headers: signedHeaders(bytes, config.key), body: bytes, signal: controller.signal });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.ok !== true) throw rpcError(payload.code || "TB_RPC_FAILED");
      return safeResult(payload.result);
    } catch (error) {
      if (error?.code?.startsWith("TB_")) throw error;
      throw rpcError(error?.name === "AbortError" ? "TB_RPC_TIMEOUT" : "TB_RPC_UNAVAILABLE");
    } finally { clearTimeout(timeout); }
  }

  async function call(operation, fields = {}, sessionId = undefined) {
    if (operation !== "health" && !serviceEpoch) {
      const health = await send("health", {}, undefined, false);
      if (typeof health?.serviceEpoch !== "string" || !health.serviceEpoch) throw rpcError("TB_RPC_PROTOCOL_INVALID");
      serviceEpoch = health.serviceEpoch;
    }
    return send(operation, fields, sessionId, operation !== "health");
  }

  function tabFor(sessionId) {
    const locator = (selector) => Object.freeze({
      count: () => call("locator_count", { selector }, sessionId).then((r) => r.value),
      isVisible: () => call("locator_is_visible", { selector }, sessionId).then((r) => r.value),
      isEnabled: async () => true,
      innerText: () => call("locator_inner_text", { selector }, sessionId).then((r) => r.value),
      getAttribute: (attribute) => call("locator_attribute", { selector, attribute }, sessionId).then((r) => r.value),
      click: () => call("locator_click", { selector }, sessionId),
    });
    return Object.freeze({
      goto: (url) => call("navigate", { url: parseTrustedNavigation(url, { certifiedOrigin }) }, sessionId).then((r) => r.url),
      close: async () => { if (sessions.has(sessionId)) { await call("close_session", {}, sessionId); sessions.delete(sessionId); } },
      playwright: Object.freeze({
        locator: (selector) => locator(selector),
        getTitle: () => call("get_title", {}, sessionId).then((r) => r.value),
        getVisibleText: () => call("get_visible_text", {}, sessionId).then((r) => r.value),
        getApprovedAttribute: (selector, attribute) => locator(selector).getAttribute(attribute),
        readApprovedDOMState: () => call("get_visible_text", {}, sessionId).then((r) => ({ title: undefined, visibleText: r.value })),
        requestJson: ({ path, method = "GET", body = undefined, csrfRequired = false } = {}) => call("request_json", { path, method, csrfRequired, ...(body === undefined ? {} : { body }) }, sessionId),
      }),
      dom_cua: Object.freeze({ get_visible_dom: () => call("get_visible_text", {}, sessionId).then((r) => r.value) }),
      capabilities: Object.freeze({ get: async (name) => name === "browserAuth" ? Object.freeze({ request: (request) => call("browser_auth", request, sessionId).then((r) => ({ status: r.status })) }) : undefined }),
    });
  }

  return Object.freeze({
    securityContext: context,
    tabs: Object.freeze({ new: async () => { const result = await call("create_session", { certifiedOrigin }); sessions.set(result.sessionId, result.identityBinding); return tabFor(result.sessionId); } }),
    close: async () => { for (const sessionId of [...sessions.keys()]) { try { await tabFor(sessionId).close(); } catch {} } },
  });
}
