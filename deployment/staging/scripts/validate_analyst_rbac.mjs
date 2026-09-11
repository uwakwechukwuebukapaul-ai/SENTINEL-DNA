import { pathToFileURL } from "node:url";
import { readEvidenceAndValidate, validateRbacEnforcement } from "./controlled_analyst_pilot_evidence_validation.mjs";

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  const result = await readEvidenceAndValidate(process.argv[2], validateRbacEnforcement);
  console.log(JSON.stringify(result));
  process.exit(result.status === "PASS" ? 0 : 2);
}
