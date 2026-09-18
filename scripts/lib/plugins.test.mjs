import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import {
  checkPluginKind,
  listPluginDirs,
  manifestPath,
  pluginComponents,
  pluginKind,
  pluginsDir,
  readJson,
  readmeKind,
  rootDir,
} from "./plugins.mjs";

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

function fixture(layout) {
  const dir = mkdtempSync(join(tmpdir(), "ce-kind-"));
  for (const [path, content] of Object.entries(layout)) {
    mkdirSync(join(dir, path, ".."), { recursive: true });
    writeFileSync(join(dir, path), content);
  }
  return dir;
}

test("pluginKind: exactly one skill and nothing else is skill-only", () => {
  const dir = fixture({ "skills/a/SKILL.md": "x" });
  assert.equal(pluginKind(pluginComponents(dir, {})), "skill-only");
});

test("pluginKind: exactly one agent and nothing else is agent-only", () => {
  const dir = fixture({ "agents/a.md": "x" });
  assert.equal(pluginKind(pluginComponents(dir, {})), "agent-only");
});

test("pluginKind: anything more is a bundle", () => {
  assert.equal(
    pluginKind(pluginComponents(fixture({ "skills/a/SKILL.md": "x", "agents/b.md": "x" }), {})),
    "bundle",
  );
  assert.equal(
    pluginKind(
      pluginComponents(fixture({ "skills/a/SKILL.md": "x", "hooks/hooks.json": "{}" }), {}),
    ),
    "bundle",
  );
  assert.equal(
    pluginKind(pluginComponents(fixture({ "skills/a/SKILL.md": "x" }), { mcpServers: {} })),
    "bundle",
  );
  assert.equal(
    pluginKind(pluginComponents(fixture({ "README.md": "x" }), { dependencies: ["a"] })),
    "bundle",
  );
});

test("readmeKind reads the README Kind line", () => {
  assert.equal(readmeKind("# X\n\n**Kind:** `skill-only` — exactly one skill.\n"), "skill-only");
  assert.equal(readmeKind("# X\n"), null);
  assert.equal(readmeKind(null), null);
});

test("checkPluginKind reports a README that disagrees with the structure", () => {
  const dir = fixture({
    "demo/skills/a/SKILL.md": "x",
    "demo/agents/b.md": "x",
    "demo/README.md": "**Kind:** `skill-only` — one skill.\n",
  });
  assert.match(
    checkPluginKind("demo", {}, dir),
    /declares Kind `skill-only` but its structure is `bundle`/,
  );
  writeFileSync(join(dir, "demo/README.md"), "**Kind:** `bundle` — several.\n");
  assert.equal(checkPluginKind("demo", {}, dir), null);
});
