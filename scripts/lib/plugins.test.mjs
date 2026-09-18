import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { listPluginDirs, manifestPath, pluginsDir, readJson, rootDir } from "./plugins.mjs";

test("listPluginDirs returns sorted directories and ignores files", () => {
  const dir = mkdtempSync(join(tmpdir(), "ce-plugins-"));
  mkdirSync(join(dir, "zeta"));
  mkdirSync(join(dir, "alpha"));
  writeFileSync(join(dir, "README.md"), "");
  assert.deepEqual(listPluginDirs(dir), ["alpha", "zeta"]);
});

test("listPluginDirs returns [] when the directory does not exist", () => {
  assert.deepEqual(listPluginDirs(join(tmpdir(), "ce-does-not-exist-404")), []);
});

test("manifestPath points at .claude-plugin/plugin.json", () => {
  assert.equal(manifestPath("demo", "/x/plugins"), "/x/plugins/demo/.claude-plugin/plugin.json");
});

test("rootDir is the repository root", () => {
  assert.equal(readJson(join(rootDir, "package.json")).name, "claude-essentials");
  assert.equal(pluginsDir, join(rootDir, "plugins"));
});
