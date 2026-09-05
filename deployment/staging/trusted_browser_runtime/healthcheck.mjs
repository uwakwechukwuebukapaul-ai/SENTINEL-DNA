import { assertProductionConfiguration } from "./runtime-service.mjs";

try {
  await assertProductionConfiguration();
  process.stdout.write("PASS\n");
} catch (error) {
  process.stdout.write(`${error?.code || "TB_HEALTHCHECK_BLOCKED"}\n`);
  process.exitCode = 1;
}
