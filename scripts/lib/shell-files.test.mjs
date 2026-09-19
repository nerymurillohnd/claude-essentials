// @ts-check
import assert from "node:assert/strict";
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
