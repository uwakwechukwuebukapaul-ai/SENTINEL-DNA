const port = Number(process.env?.SENTINEL_DNA_EGRESS_GATEWAY_PORT);
const bind = process.env?.SENTINEL_DNA_EGRESS_GATEWAY_BIND;
if (!Number.isInteger(port) || !bind) process.exit(1);
try {
  const response = await fetch(`http://${bind}:${port}/healthz`);
  if (!response.ok) process.exit(1);
  const body = await response.json();
  if (body.ok !== true && body.status !== "ready") process.exit(1);
} catch { process.exit(1); }
