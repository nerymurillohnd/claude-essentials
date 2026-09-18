import assert from "node:assert/strict";
import { test } from "node:test";
import {
  bumpLabelFor,
  planVersions,
  pluginsTouched,
  runtimeManifestChanged,
  untaggedVersions,
} from "./version-plan.mjs";

const manifest = (name, version) => ({ name, version, description: "d" });
const changelog = (...versions) =>
  versions.map((v) => `## [${v}] - 2026-09-18\n\n### Fixed\n\n- Fix for ${v}.\n`).join("\n");

function plan(overrides) {
  return planVersions({
    changedFiles: [],
    base: new Map(),
    head: new Map(),
    changelogs: new Map(),
    renames: {},
    existingTags: new Set(),
    deferred: false,
    ...overrides,
  });
}

test("pluginsTouched keeps only files inside plugin directories", () => {
  assert.deepEqual(
    pluginsTouched([
      "plugins/b/x.md",
      "plugins/a/.claude-plugin/plugin.json",
      "plugins/README.md",
      "docs/x.md",
    ]),
    ["a", "b"],
  );
});

test("no plugin changes → bump: none", () => {
  const result = plan({ changedFiles: ["docs/README.md"] });
  assert.deepEqual(result, { plugins: [], bumpLabel: "bump: none", ok: true });
});

test("patch bump with changelog entry passes", () => {
  const result = plan({
    changedFiles: ["plugins/demo/skills/x/SKILL.md", "plugins/demo/.claude-plugin/plugin.json"],
    base: new Map([["demo", manifest("demo", "1.0.0")]]),
    head: new Map([["demo", manifest("demo", "1.0.1")]]),
    changelogs: new Map([["demo", changelog("1.0.1", "1.0.0")]]),
  });
  assert.equal(result.ok, true);
  assert.equal(result.plugins[0].status, "bumped");
  assert.equal(result.plugins[0].bump, "patch");
  assert.equal(result.bumpLabel, "bump: patch");
});

test("runtime change without bump fails unless deferred", () => {
  const input = {
    changedFiles: ["plugins/demo/skills/x/SKILL.md"],
    base: new Map([["demo", manifest("demo", "1.0.0")]]),
    head: new Map([["demo", manifest("demo", "1.0.0")]]),
    changelogs: new Map([["demo", changelog("1.0.0")]]),
  };
  const failed = plan(input);
  assert.equal(failed.ok, false);
  assert.match(failed.plugins[0].errors[0], /still 1\.0\.0/);
  assert.equal(failed.bumpLabel, null);

  const deferred = plan({ ...input, deferred: true });
  assert.equal(deferred.ok, true);
  assert.equal(deferred.plugins[0].status, "deferred");
  assert.equal(deferred.bumpLabel, "bump: none");
});

test("changes Claude never loads need no bump", () => {
  const result = plan({
    changedFiles: [
      "plugins/demo/README.md",
      "plugins/demo/CHANGELOG.md",
      "plugins/demo/LICENSE.md",
      "plugins/demo/docs/guide/usage.md",
    ],
    base: new Map([["demo", manifest("demo", "1.0.0")]]),
    head: new Map([["demo", manifest("demo", "1.0.0")]]),
    changelogs: new Map([["demo", changelog("1.0.0")]]),
  });
  assert.equal(result.ok, true);
  assert.equal(result.plugins[0].status, "exempt");
  assert.equal(result.bumpLabel, "bump: none");
});

test("a one-character fix in a SKILL.md still needs a bump, and the error names the file", () => {
  const result = plan({
    changedFiles: ["plugins/demo/README.md", "plugins/demo/skills/x/SKILL.md"],
    base: new Map([["demo", manifest("demo", "1.0.0")]]),
    head: new Map([["demo", manifest("demo", "1.0.0")]]),
    changelogs: new Map([["demo", changelog("1.0.0")]]),
  });
  assert.equal(result.ok, false);
  assert.match(result.plugins[0].errors[0], /skills\/x\/SKILL\.md/);
  assert.doesNotMatch(result.plugins[0].errors[0], /README/);
});

test("unknown paths are treated as runtime (the exempt list is closed)", () => {
  const result = plan({
    changedFiles: ["plugins/demo/assets/logo.png"],
    base: new Map([["demo", manifest("demo", "1.0.0")]]),
    head: new Map([["demo", manifest("demo", "1.0.0")]]),
    changelogs: new Map([["demo", changelog("1.0.0")]]),
  });
  assert.equal(result.ok, false);
});

test("plugin.json metadata edits are exempt; component or dependency edits are not", () => {
  const before = { ...manifest("demo", "1.0.0"), keywords: ["a"], dependencies: ["x"] };
  const metadataOnly = plan({
    changedFiles: ["plugins/demo/.claude-plugin/plugin.json"],
    base: new Map([["demo", before]]),
    head: new Map([["demo", { ...before, description: "Better words.", keywords: ["a", "b"] }]]),
    changelogs: new Map([["demo", changelog("1.0.0")]]),
  });
  assert.equal(metadataOnly.plugins[0].status, "exempt");

  const dependencies = plan({
    changedFiles: ["plugins/demo/.claude-plugin/plugin.json"],
    base: new Map([["demo", before]]),
    head: new Map([["demo", { ...before, dependencies: ["x", "y"] }]]),
    changelogs: new Map([["demo", changelog("1.0.0")]]),
  });
  assert.equal(dependencies.ok, false);
});

test("runtimeManifestChanged ignores key order and metadata", () => {
  assert.equal(
    runtimeManifestChanged({ a: 1, b: { c: 2, d: 3 } }, { b: { d: 3, c: 2 }, a: 1 }),
    false,
  );
  assert.equal(
    runtimeManifestChanged({ hooks: "./h.json" }, { hooks: "./h.json", description: "x" }),
    false,
  );
  assert.equal(runtimeManifestChanged({ hooks: "./h.json" }, { hooks: "./other.json" }), true);
});

test("version going backwards fails", () => {
  const result = plan({
    changedFiles: ["plugins/demo/.claude-plugin/plugin.json"],
    base: new Map([["demo", manifest("demo", "1.2.0")]]),
    head: new Map([["demo", manifest("demo", "1.1.9")]]),
    changelogs: new Map([["demo", changelog("1.1.9")]]),
  });
  assert.equal(result.ok, false);
  assert.match(result.plugins[0].errors[0], /backwards/);
});

test("new plugin needs a changelog entry for its first version", () => {
  const input = {
    changedFiles: ["plugins/fresh/.claude-plugin/plugin.json"],
    head: new Map([["fresh", manifest("fresh", "0.1.0")]]),
  };
  const missing = plan({ ...input, changelogs: new Map([["fresh", "# Changelog\n"]]) });
  assert.equal(missing.ok, false);
  assert.match(missing.plugins[0].errors[0], /no "## \[0\.1\.0\] - YYYY-MM-DD" entry/);

  const good = plan({ ...input, changelogs: new Map([["fresh", changelog("0.1.0")]]) });
  assert.equal(good.ok, true);
  assert.equal(good.plugins[0].status, "new");
  assert.equal(good.bumpLabel, "bump: initial");
});

test("prerelease and graduation are classified", () => {
  const pre = plan({
    changedFiles: ["plugins/demo/x"],
    base: new Map([["demo", manifest("demo", "1.0.0")]]),
    head: new Map([["demo", manifest("demo", "2.0.0-beta.1")]]),
    changelogs: new Map([["demo", changelog("2.0.0-beta.1")]]),
  });
  assert.equal(pre.plugins[0].bump, "prerelease");
  assert.equal(pre.bumpLabel, "bump: prerelease");

  const graduation = plan({
    changedFiles: ["plugins/demo/x"],
    base: new Map([["demo", manifest("demo", "2.0.0-rc.1")]]),
    head: new Map([["demo", manifest("demo", "2.0.0")]]),
    changelogs: new Map([["demo", changelog("2.0.0")]]),
  });
  assert.equal(graduation.plugins[0].bump, "major");
});

test("reusing an existing tag fails", () => {
  const result = plan({
    changedFiles: ["plugins/demo/x"],
    base: new Map([["demo", manifest("demo", "1.0.0")]]),
    head: new Map([["demo", manifest("demo", "1.1.0")]]),
    changelogs: new Map([["demo", changelog("1.1.0")]]),
    existingTags: new Set(["demo--v1.1.0"]),
  });
  assert.equal(result.ok, false);
  assert.match(result.plugins[0].errors[0], /demo--v1\.1\.0 already exists/);
});

test("non-canonical semver is rejected", () => {
  const result = plan({
    changedFiles: ["plugins/demo/x"],
    head: new Map([["demo", manifest("demo", "v1.0.0")]]),
    changelogs: new Map([["demo", changelog("1.0.0")]]),
  });
  assert.equal(result.ok, false);
  assert.match(result.plugins[0].errors[0], /valid semver/);
});

test("removed plugin requires a renames entry and counts as major", () => {
  const input = {
    changedFiles: ["plugins/gone/.claude-plugin/plugin.json"],
    base: new Map([["gone", manifest("gone", "1.0.0")]]),
    head: new Map([["gone", null]]),
  };
  const missing = plan(input);
  assert.equal(missing.ok, false);
  assert.match(missing.plugins[0].errors[0], /renames/);

  const recorded = plan({ ...input, renames: { gone: null } });
  assert.equal(recorded.ok, true);
  assert.equal(recorded.plugins[0].status, "removed");
  assert.equal(recorded.bumpLabel, "bump: major");
});

test("the highest bump across plugins wins", () => {
  assert.equal(
    bumpLabelFor([
      { status: "bumped", bump: "patch", errors: [] },
      { status: "bumped", bump: "minor", errors: [] },
      { status: "new", bump: "initial", errors: [] },
    ]),
    "bump: minor",
  );
});

test("untaggedVersions lists versions without a tag", () => {
  const { versions, errors } = untaggedVersions(
    [
      { name: "a", version: "1.0.0", changelog: changelog("1.0.0") },
      { name: "b", version: "2.0.0-beta.1", changelog: changelog("2.0.0-beta.1") },
      { name: "c", version: "1.0.0", changelog: changelog("1.0.0") },
    ],
    new Set(["c--v1.0.0"]),
  );
  assert.deepEqual(errors, []);
  assert.deepEqual(
    versions.map((v) => [v.tag, v.prerelease]),
    [
      ["a--v1.0.0", false],
      ["b--v2.0.0-beta.1", true],
    ],
  );
});

test("untaggedVersions reports missing changelog entries and bad versions", () => {
  const { versions, errors } = untaggedVersions(
    [
      { name: "a", version: "1.0.0", changelog: "# Changelog\n" },
      { name: "b", version: undefined, changelog: null },
    ],
    new Set(),
  );
  assert.deepEqual(versions, []);
  assert.equal(errors.length, 2);
});
