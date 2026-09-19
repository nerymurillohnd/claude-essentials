// @ts-check
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { isShellScript, listShellFiles } from "./shell-files.mjs";

test("isShellScript accepts .sh files and sh/bash shebangs", () => {
  assert.equal(isShellScript("hooks/a.sh", ""), true);
  assert.equal(isShellScript("bin/tool", "#!/usr/bin/env bash"), true);
  assert.equal(isShellScript("bin/tool", "#!/bin/sh -e"), true);
  assert.equal(isShellScript("bin/tool", "#!/bin/bash"), true);
});

test("isShellScript rejects other interpreters and plain files", () => {
  assert.equal(isShellScript("scripts/x.mjs", "#!/usr/bin/env node"), false);
  assert.equal(isShellScript("bin/tool", "#!/usr/bin/env zsh"), false);
  assert.equal(isShellScript("bin/tool", "#!/usr/bin/env fish"), false);
  assert.equal(isShellScript("README.md", "# Title"), false);
});

test("listShellFiles finds every tracked hook script in this repo", () => {
  const files = listShellFiles();
  for (const hook of [".claude/hooks/post-edit.sh", ".claude/hooks/lib/plugin-paths.sh"]) {
    assert.ok(files.includes(hook), `${hook} missing from ${files.join(", ")}`);
  }
  assert.ok(files.every((file) => !file.startsWith("node_modules/")));
});

test("listShellFiles includes new untracked scripts but not ignored or deleted ones", () => {
  // A new plugin's test suite must run (and be linted) before its first commit;
  // otherwise `npm run check` is green without having looked at it.
  const root = mkdtempSync(join(tmpdir(), "shell-files-"));
  try {
    const git = (/** @type {string[]} */ ...args) =>
      execFileSync("git", args, { cwd: root, stdio: "ignore" });
    git("init", "-q");
    writeFileSync(join(root, ".gitignore"), "ignored.sh\n");
    for (const name of ["tracked.sh", "deleted.sh", "untracked.sh", "ignored.sh"]) {
      writeFileSync(join(root, name), "#!/usr/bin/env bash\n");
    }
    git("add", ".gitignore", "tracked.sh", "deleted.sh");
    rmSync(join(root, "deleted.sh"));
    assert.deepEqual(listShellFiles(root).sort(), ["tracked.sh", "untracked.sh"]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
