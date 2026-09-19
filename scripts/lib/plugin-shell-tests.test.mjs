// @ts-check
// Runs every tracked plugin shell test suite (plugins/**/test-*.sh) so CI
// exercises what plugins ship. Each suite runs under `bash` from PATH and, when
// it is a different binary, under /bin/bash too (macOS ships bash 3.2 there, the
// oldest shell a public plugin must support).
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, realpathSync } from "node:fs";
import { test } from "node:test";
import { rootDir } from "./plugins.mjs";
import { listShellFiles } from "./shell-files.mjs";

const suites = listShellFiles().filter((file) => /^plugins\/.+\/test-[^/]+\.sh$/.test(file));

/** @returns {string[]} Distinct bash binaries to run each suite with. */
function bashBinaries() {
  const which = spawnSync("bash", ["-c", "command -v bash"], { encoding: "utf8" });
  const onPath = which.status === 0 ? which.stdout.trim() : "";
  /** @type {string[]} */
  const found = [];
  for (const candidate of [onPath, "/bin/bash"]) {
    if (candidate === "" || !existsSync(candidate)) continue;
    const real = realpathSync(candidate);
    if (!found.some((seen) => realpathSync(seen) === real)) found.push(candidate);
  }
  return found;
}

test("plugin shell test suites are discovered", () => {
  assert.ok(suites.length > 0, "expected at least one plugins/**/test-*.sh suite");
});

for (const suite of suites) {
  for (const bash of bashBinaries()) {
    test(`${suite} passes under ${bash}`, () => {
      const result = spawnSync(bash, [suite], {
        cwd: rootDir,
        encoding: "utf8",
        env: { ...process.env, BNV_TEST_BASH: bash },
      });
      assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
    });
  }
}
