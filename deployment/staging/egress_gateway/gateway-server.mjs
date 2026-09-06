import { createServer } from "node:http";
import { loadEgressPolicy, authorizeConnection } from "../scripts/trusted_browser_service/policy/egress-policy.mjs";

export const GATEWAY_PORT_ENV = "SENTINEL_DNA_EGRESS_GATEWAY_PORT";
export const GATEWAY_BIND_ENV = "SENTINEL_DNA_EGRESS_GATEWAY_BIND";

export function createEgressGateway({ policyLoader = loadEgressPolicy, connect = undefined } = {}) {
  let state = { ready: false, policyDigest: null };
  const server = createServer(async (request, response) => {
    if (request.method === "GET" && request.url === "/healthz") {
      response.writeHead(state.ready ? 200 : 503, { "content-type": "application/json" });
      response.end(JSON.stringify({ ok: state.ready, status: state.ready ? "ready" : "blocked", policyDigest: state.policyDigest }));
      return;
    }
    response.writeHead(405, { "content-type": "application/json" });
    response.end(JSON.stringify({ ok: false, code: "TB_EGRESS_METHOD_REJECTED" }));
  });
  return Object.freeze({
    server,
    async initialize() {
      const loaded = await policyLoader();
      state = { ready: true, policyDigest: loaded.digest };
      return Object.freeze({ status: "ready", policyDigest: loaded.digest });
    },
    async authorize(url, previousAddresses) {
      if (!state.ready) { const error = new Error("TB_EGRESS_GATEWAY_NOT_READY"); error.code = "TB_EGRESS_GATEWAY_NOT_READY"; throw error; }
      const loaded = await policyLoader();
      if (loaded.digest !== state.policyDigest) { const error = new Error("TB_EGRESS_POLICY_CHANGED"); error.code = "TB_EGRESS_POLICY_CHANGED"; throw error; }
      return authorizeConnection({ url, policy: loaded.policy, previousAddresses });
    },
  });
}

export async function startEgressGateway() {
  const gateway = createEgressGateway();
  await gateway.initialize();
  const port = Number(process.env?.[GATEWAY_PORT_ENV]);
  const bind = process.env?.[GATEWAY_BIND_ENV];
  if (!Number.isInteger(port) || port < 1 || port > 65535 || typeof bind !== "string" || !bind.trim()) {
    const error = new Error("TB_EGRESS_CONFIGURATION_INVALID"); error.code = "TB_EGRESS_CONFIGURATION_INVALID"; throw error;
  }
  await new Promise((resolve, reject) => { gateway.server.once("error", reject); gateway.server.listen(port, bind, resolve); });
  return gateway;
}

if (process.argv[1]?.endsWith("gateway-server.mjs")) startEgressGateway().catch((error) => { process.stderr.write(`${error.code || "TB_EGRESS_STARTUP_FAILED"}\n`); process.exitCode = 1; });
