import { createApprovedBrowser } from "./trusted_browser_execution_adapter.mjs";
import { runControlledAnalystPilot } from "./controlled_analyst_pilot_runner.mjs";
import {
  checkControlledPilotReadiness,
  READINESS_READY_STATUS,
} from "./check_controlled_pilot_readiness.mjs";
import { fileURLToPath } from "node:url";

function operatorRunId() {
  if (typeof process !== "undefined" && process.argv?.[2]) return process.argv[2];
  return "pilot-manual-001";
}

export async function executeControlledAnalystPilot({ runId = operatorRunId() } = {}) {
  const readiness = await checkControlledPilotReadiness();
  if (readiness.status !== READINESS_READY_STATUS) {
    const blocker = readiness.checks.find((check) => check.status !== "PASS");
    const error = new Error("controlled analyst pilot readiness is blocked");
    error.code = "TB_PILOT_READINESS_BLOCKED";
    error.readiness = {
      status: readiness.status,
      blocker: blocker ? { name: blocker.name, status: blocker.status, reason: blocker.reason } : undefined,
    };
    throw error;
  }
  const browser = await createApprovedBrowser();
  return runControlledAnalystPilot({ browser, runId });
}

function safeSummary(result) {
  return {
    status: result.status,
    evidence: result.evidence,
    result_count: Array.isArray(result.results) ? result.results.length : 0,
    blockers: result.results?.filter((item) => item.status === "FAIL" || item.status === "NOT_MEASURED" || item.status === "NOT_PERFORMED").map((item) => item.check) ?? [],
  };
}

const invokedAsMain = typeof process !== "undefined" && process.argv?.[1] &&
  fileURLToPath(import.meta.url) === process.argv[1];

if (invokedAsMain) {
  try {
    const result = await executeControlledAnalystPilot();
    console.log(JSON.stringify(safeSummary(result), null, 2));
  } catch (error) {
    if (error?.code === "TB_PILOT_READINESS_BLOCKED") {
      console.log(JSON.stringify({ status: "BLOCKED_WITH_REASON", ...error.readiness }, null, 2));
    } else {
      console.log(JSON.stringify({ status: "BLOCKED_WITH_REASON", blocker: { name: "trusted_browser_execution", status: "BLOCKED", reason: "TB_RUNTIME_UNAVAILABLE" } }, null, 2));
    }
    process.exitCode = 1;
  }
}
