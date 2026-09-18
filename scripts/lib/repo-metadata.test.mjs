import assert from "node:assert/strict";
import { test } from "node:test";
import { pluginDropdownOptions } from "./issue-forms.mjs";
import { listPluginDirs, rootDir } from "./plugins.mjs";
import { checkIssueForm, checkLabels, validateRepoMetadata } from "./repo-metadata.mjs";

const ok = { name: "type: bug", color: "d73a4a", description: "Broken" };

test("checkLabels accepts a valid label set", () => {
  assert.deepEqual(checkLabels([ok], ["type: bug"]), []);
});

test("checkLabels reports duplicates, bad colors, derived prefixes, long text, missing required", () => {
  const errors = checkLabels(
    [
      ok,
      { ...ok, name: "Type: Bug" },
      { name: "plugin: x", color: "ABCDEF", description: "x".repeat(101) },
    ],
    ["type: bug", "status: needs-triage"],
  );
  assert.equal(errors.length, 5);
  assert.ok(errors.some((e) => e.includes("duplicate")));
  assert.ok(errors.some((e) => e.includes("derived")));
  assert.ok(errors.some((e) => e.includes("6 lowercase hex")));
  assert.ok(errors.some((e) => e.includes("1–100")));
  assert.ok(errors.some((e) => e.includes('"status: needs-triage" is required')));
});

test("checkLabels rejects an alias that collides with a label name or another alias", () => {
  const errors = checkLabels(
    [
      { name: "type: bug", color: "d73a4a", description: "d", aliases: ["bug"] },
      { name: "bug", color: "d73a4a", description: "d" },
      { name: "type: broken", color: "d73a4a", description: "d", aliases: ["bug"] },
    ],
    [],
  );
  assert.ok(errors.some((e) => e.includes('alias "bug" is also a label name')));
  assert.ok(errors.some((e) => e.includes('alias "bug" is already an alias of another label')));
});

test("checkIssueForm reports unknown labels, missing keys, and a stale dropdown", () => {
  const errors = checkIssueForm(
    "bug-report.yml",
    {
      name: "Bug",
      body: [
        {
          type: "dropdown",
          id: "plugin",
          attributes: { label: "Affected plugin", options: ["old"] },
        },
      ],
      labels: ["type: bug", "nope"],
    },
    { labelNames: new Set(["type: bug"]), pluginNames: ["demo"] },
  );
  assert.deepEqual(errors, [
    '.github/ISSUE_TEMPLATE/bug-report.yml: missing "description"',
    '.github/ISSUE_TEMPLATE/bug-report.yml: label "nope" is not in .github/labels.json',
    '.github/ISSUE_TEMPLATE/bug-report.yml: "plugin" dropdown is stale — run npm run generate',
  ]);
});

test("checkIssueForm accepts a current form", () => {
  const form = {
    name: "Bug",
    description: "d",
    labels: "type: bug",
    body: [
      {
        type: "dropdown",
        id: "plugin",
        attributes: { label: "Affected plugin", options: pluginDropdownOptions(["demo"]) },
      },
    ],
  };
  assert.deepEqual(
    checkIssueForm("f.yml", form, { labelNames: new Set(["type: bug"]), pluginNames: ["demo"] }),
    [],
  );
});

test("the committed labels and issue forms are valid", () => {
  assert.deepEqual(validateRepoMetadata(rootDir, listPluginDirs()), []);
});
