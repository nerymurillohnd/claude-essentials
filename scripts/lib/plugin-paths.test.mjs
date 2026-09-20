// @ts-check
// Parity between the two implementations of "which plugin files are runtime"
// (ADR-0003): scripts/lib/version-plan.mjs (CI's version-check) and
// .claude/hooks/lib/plugin-paths.sh (session-start/post-edit hooks). The hooks
// run the real bash functions here, so a drift fails `npm test`, not a review.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { join } from "node:path";
import { test } from "node:test";
import { rootDir } from "./plugins.mjs";
import { EXEMPT_FILE, METADATA_KEYS } from "./version-plan.mjs";

const library = join(rootDir, ".claude", "hooks", "lib", "plugin-paths.sh");

/**
 * Runs a snippet with plugin-paths.sh sourced; returns stdout.
 * @param {string} script
 * @param {string[]} args
 * @param {string} [input]
 */
function bash(script, args, input) {
  return execFileSync("bash", ["-c", `source "$0"; ${script}`, library, ...args], {
    encoding: "utf8",
    ...(input === undefined ? {} : { input }),
  });
}

/** @param {string} rel */
const bashExempt = (rel) =>
  bash('if plugin_path_is_exempt "$1"; then echo exempt; else echo runtime; fi', [rel]).trim();

test("bash plugin_path_is_exempt agrees with EXEMPT_FILE on every edge case", () => {
  const paths = [
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "LICENSE.",
    "LICENSE.d/notes.md",
    "docs/x.md",
    "docs/a/b.md",
    "docs/",
    "docs",
    "readme.md",
    "README.txt",
    "CHANGELOG.md.bak",
    "sub/README.md",
    "skills/x/SKILL.md",
    "agents/a.md",
    "hooks/hooks.json",
    ".claude-plugin/plugin.json",
  ];
  for (const rel of paths) {
    const expected = EXEMPT_FILE.test(rel) ? "exempt" : "runtime";
    assert.equal(bashExempt(rel), expected, `${rel}: bash and EXEMPT_FILE disagree`);
  }
});

test("bash plugin_manifest_runtime_json strips exactly METADATA_KEYS", () => {
  const runtimeFields = { name: "demo", skills: "./skills/", hooks: "./hooks/hooks.json" };
  const manifest = {
    ...Object.fromEntries([...METADATA_KEYS].map((key) => [key, `value of ${key}`])),
    ...runtimeFields,
  };
  const stripped = JSON.parse(bash("plugin_manifest_runtime_json", [], JSON.stringify(manifest)));
  assert.deepEqual(stripped, runtimeFields);
});

test("bash plugin_manifest_runtime_json ignores a metadata-only edit", () => {
  const base = { name: "demo", version: "1.0.0", skills: "./skills/" };
  const edited = {
    ...base,
    metadata: { marketplace: { category: "security", tags: ["git-hooks", "guardrails"] } },
  };
  const strip = (/** @type {object} */ manifest) =>
    bash("plugin_manifest_runtime_json", [], JSON.stringify(manifest));
  assert.equal(strip(edited), strip(base));
  assert.notEqual(strip({ ...base, skills: "./other/" }), strip(base));
});
