import { spawnSync } from "node:child_process";
import { readdirSync } from "node:fs";
import { join } from "node:path";

function stagingTests(directory) {
  return readdirSync(directory, { withFileTypes: true })
    .flatMap((entry) => {
      const path = join(directory, entry.name);
      return entry.isDirectory() ? stagingTests(path) : [path];
    })
    .filter((path) => path.endsWith(".test.mjs"))
    .sort();
}

// npm callers commonly pass Jest's --runInBand flag. Node's test runner is
// already deterministic for this suite, so accept that compatibility flag but
// do not forward it as an unsupported Node option.
const forwardedArgs = process.argv.slice(2).filter((argument) => argument !== "--runInBand");
const result = spawnSync(
  process.execPath,
  ["--test", ...stagingTests("tests/staging"), ...forwardedArgs],
  { stdio: "inherit" },
);

if (result.error) {
  console.error(result.error.message);
  process.exitCode = 1;
} else {
  process.exitCode = result.status ?? 1;
}
