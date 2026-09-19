// @ts-check
import assert from "node:assert/strict";
import { test } from "node:test";
import { AREA_LABELS } from "./labels.mjs";
import {
  AREA_RULES,
  areaLabels,
  authorReplyChanges,
  formField,
  issueLabels,
  isValidPluginName,
  pluginLabels,
  reconcile,
} from "./triage.mjs";

test("every area rule uses a taxonomy label", () => {
  assert.deepEqual(AREA_RULES.map((r) => r.label).sort(), [...AREA_LABELS].sort());
});

test("areaLabels maps paths to sorted, unique area labels", () => {
  assert.deepEqual(areaLabels(["plugins/a/x.md", "docs/y.md", "README.md"]), [
    "area: docs",
    "area: plugins",
  ]);
  assert.deepEqual(areaLabels([".github/workflows/ci.yml"]), ["area: ci"]);
  assert.deepEqual(areaLabels([".github/ISSUE_TEMPLATE/bug-report.yml"]), ["area: community"]);
  assert.deepEqual(areaLabels(["CONTRIBUTING.md"]), ["area: community", "area: docs"]);
  assert.deepEqual(areaLabels(["schemas/plugin.schema.json", "scripts/x.mjs"]), [
    "area: catalog",
    "area: tooling",
  ]);
  assert.deepEqual(areaLabels(["templates/README.md"]), ["area: templates"]);
});

test("pluginLabels derives one label per touched plugin", () => {
  assert.deepEqual(pluginLabels(["plugins/b/x", "plugins/a/y", "plugins/README.md"]), [
    "plugin: a",
    "plugin: b",
  ]);
});

test("isValidPluginName accepts kebab-case names within the length limit", () => {
  assert.equal(isValidPluginName("demo-skill"), true);
  assert.equal(isValidPluginName("Demo-Skill"), false);
  assert.equal(isValidPluginName("demo_skill"), false);
  assert.equal(isValidPluginName("a".repeat(43)), false);
  assert.equal(isValidPluginName("a".repeat(42)), true);
});

test("pluginLabels silently drops touched names that fail the plugin-name rule", () => {
  const overlong = "a".repeat(43);
  assert.deepEqual(
    pluginLabels([
      "plugins/demo-skill/x",
      `plugins/${overlong}/x`,
      "plugins/Bad_Name/x",
      "plugins/good-one/y",
    ]),
    ["plugin: demo-skill", "plugin: good-one"],
  );
});

const body = "### Affected plugin\n\ndemo-skill\n\n### Plugin version\n\n1.0.0\n";

test("formField reads rendered issue-form sections", () => {
  assert.equal(formField(body, "Affected plugin"), "demo-skill");
  assert.equal(formField(body, "Plugin version"), "1.0.0");
  assert.equal(formField("### Relevant output\n\n_No response_\n", "Relevant output"), null);
  assert.equal(formField(null, "Affected plugin"), null);
});

test("issueLabels maps the dropdown to plugin or catalog labels", () => {
  assert.deepEqual(issueLabels(body, ["demo-skill"]), ["plugin: demo-skill"]);
  assert.deepEqual(issueLabels(body, ["other"]), []);
  assert.deepEqual(issueLabels("### Affected plugin\n\nMarketplace catalog / installation\n", []), [
    "area: catalog",
  ]);
  assert.deepEqual(issueLabels("### Affected plugin\n\nNot sure\n", []), []);
});

test("authorReplyChanges moves needs-info back to triage only for the author", () => {
  const labels = ["type: bug", "status: needs-info", "status: stale"];
  assert.deepEqual(authorReplyChanges({ labels, author: "u", commenter: "u" }), {
    add: ["status: needs-triage"],
    remove: ["status: needs-info", "status: stale"],
  });
  assert.deepEqual(authorReplyChanges({ labels, author: "u", commenter: "maintainer" }), {
    add: [],
    remove: [],
  });
  assert.deepEqual(authorReplyChanges({ labels: ["type: bug"], author: "u", commenter: "u" }), {
    add: [],
    remove: [],
  });
});

test("reconcile only removes bot-managed labels and never the deferred label", () => {
  assert.deepEqual(
    reconcile(
      ["bump: patch", "plugin: old", "type: bug", "bump: deferred"],
      ["bump: minor", "plugin: new"],
    ),
    { add: ["bump: minor", "plugin: new"], remove: ["bump: patch", "plugin: old"] },
  );
});
