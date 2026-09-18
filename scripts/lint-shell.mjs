#!/usr/bin/env node
// Lints every tracked shell script with ShellCheck (policy: .shellcheckrc) and
// checks formatting with shfmt (style: .editorconfig). Resolves DEBT-0003: the
// same gate the PostToolUse hook applies to Claude's edits, for every change.
import { spawnSync } from "node:child_process";
import { rootDir } from "./lib/plugins.mjs";
import { listShellFiles } from "./lib/shell-files.mjs";

const files = listShellFiles();
if (files.length === 0) {
  console.log("No shell scripts to lint.");
  process.exit(0);
}

let failed = false;
for (const [tool, args, hint] of [
  ["shellcheck", ["-x", ...files], "brew install shellcheck"],
  ["shfmt", ["-d", ...files], "brew install shfmt"],
]) {
  const result = spawnSync(tool, args, { cwd: rootDir, encoding: "utf8" });
  if (result.error?.code === "ENOENT") {
    console.error(`✗ ${tool} is not installed (${hint}).`);
    failed = true;
    continue;
  }
  if (result.status !== 0) {
    console.error(`✗ ${tool} found problems:\n${result.stdout}${result.stderr}`);
    failed = true;
    continue;
  }
  console.log(`✓ ${tool}: ${files.length} shell script(s) clean`);
}
process.exit(failed ? 1 : 0);
