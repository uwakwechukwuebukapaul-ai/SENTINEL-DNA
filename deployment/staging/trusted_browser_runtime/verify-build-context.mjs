import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const REQUIRED_DOCKERIGNORE_RULES = Object.freeze([
  ".git",
  "node_modules",
  ".npm",
  ".yarn",
  ".pnpm-store",
  ".cache",
  ".ms-playwright",
  "ms-playwright",
  "playwright-cache",
  "browser-cache",
  "custody",
  "evidence",
  "provenance",
  "artifacts",
  ".gate4-*",
  "gate4-artifact-*",
  "credentials",
  "secrets",
  ".env",
  "*.pem",
  "*.key",
  "*.crt",
  "logs",
  ".vscode",
  ".idea",
  "*.code-workspace",
  "*.log",
  "*.tmp",
  "tmp",
  "coverage",
]);

function policyError(code, details = {}) {
  const error = new Error(code);
  error.code = code;
  error.details = details;
  return error;
}

function normalizedLines(value) {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"));
}

function hasRule(lines, rule) {
  return lines.some((line) => line === rule || line === `**/${rule}` || line.startsWith(`${rule}/`) || line.startsWith(`**/${rule}/`));
}

function assertNoBroadCopy(dockerfile) {
  const broadCopy = dockerfile
    .split(/\r?\n/)
    .filter((line) => /^\s*COPY\s+/i.test(line))
    .find((line) => /^\s*COPY\s+(?:--[^\s]+\s+)?(?:\.\.?|\*|\.\/)(?:\s|$)/i.test(line));
  if (broadCopy) throw policyError("TB_BUILD_CONTEXT_BROAD_COPY", { line: broadCopy.trim() });
}

export function verifyBuildContextPolicy({
  dockerignore,
  dockerfile,
} = {}) {
  if (typeof dockerignore !== "string" || typeof dockerfile !== "string") {
    throw policyError("TB_BUILD_CONTEXT_POLICY_INPUT_INVALID");
  }
  const lines = normalizedLines(dockerignore);
  const missingRules = REQUIRED_DOCKERIGNORE_RULES.filter((rule) => !hasRule(lines, rule));
  if (missingRules.length) throw policyError("TB_BUILD_CONTEXT_POLICY_INCOMPLETE", { missingRules });
  assertNoBroadCopy(dockerfile);
  return Object.freeze({
    status: "PASS",
    requiredRules: REQUIRED_DOCKERIGNORE_RULES,
    broadCopy: false,
  });
}

export function verifyBuildContextFiles({
  contextRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../../.."),
  dockerignorePath = resolve(contextRoot, ".dockerignore"),
  dockerfilePath = resolve(contextRoot, "deployment/staging/trusted_browser_runtime/Dockerfile"),
} = {}) {
  return verifyBuildContextPolicy({
    dockerignore: readFileSync(dockerignorePath, "utf8"),
    dockerfile: readFileSync(dockerfilePath, "utf8"),
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    process.stdout.write(`${JSON.stringify(verifyBuildContextFiles())}\n`);
  } catch (error) {
    process.stderr.write(`${error?.code || "TB_BUILD_CONTEXT_POLICY_FAILED"}\n`);
    process.exitCode = 1;
  }
}
