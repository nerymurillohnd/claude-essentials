import assert from "node:assert/strict";
import { test } from "node:test";
import {
  BUMP_LABELS,
  buildTaxonomy,
  diffLabels,
  MAX_LABEL_DESCRIPTION,
  pluginLabel,
} from "./labels.mjs";
import { bumpLabelFor } from "./version-plan.mjs";

const label = (name, color = "aaaaaa", description = "d", extra = {}) => ({
  name,
  color,
  description,
  ...extra,
});

test("pluginLabel derives name and truncates description to the GitHub limit", () => {
  const derived = pluginLabel({ name: "demo", description: "x".repeat(150) });
  assert.equal(derived.name, "plugin: demo");
  assert.equal(derived.color, "5319e7");
  assert.equal(derived.description.length, MAX_LABEL_DESCRIPTION);
  assert.ok(derived.description.endsWith("…"));
});

test("buildTaxonomy appends one plugin label per manifest", () => {
  const taxonomy = buildTaxonomy([label("type: bug")], [{ name: "a", description: "A." }]);
  assert.deepEqual(
    taxonomy.map((l) => l.name),
    ["type: bug", "plugin: a"],
  );
});

test("diffLabels creates missing labels and leaves equal ones alone", () => {
  assert.deepEqual(diffLabels([label("x")], [label("x"), label("y")]), [
    { op: "create", label: label("y") },
  ]);
});

test("diffLabels updates color or description and matches names case-insensitively", () => {
  const ops = diffLabels([label("Type: Bug", "FFFFFF")], [label("type: bug", "d73a4a")]);
  assert.deepEqual(ops, [{ op: "update", from: "Type: Bug", label: label("type: bug", "d73a4a") }]);
});

test("diffLabels renames an alias instead of creating a duplicate", () => {
  const want = label("type: bug", "d73a4a", "d", { aliases: ["bug"] });
  assert.deepEqual(diffLabels([label("bug", "d73a4a", "Something isn't working")], [want]), [
    { op: "update", from: "bug", label: want },
  ]);
});

test("diffLabels deletes unclaimed labels only when pruning", () => {
  const current = [label("x"), label("wontfix")];
  assert.deepEqual(diffLabels(current, [label("x")]), []);
  assert.deepEqual(diffLabels(current, [label("x")], { prune: true }), [
    { op: "delete", from: "wontfix" },
  ]);
});

test("every label bumpLabelFor can compute is in BUMP_LABELS", () => {
  for (const bump of ["initial", "prerelease", "patch", "minor", "major", null]) {
    const computed = bumpLabelFor([{ status: "bumped", bump, errors: [] }]);
    assert.ok(BUMP_LABELS.includes(computed), computed);
  }
});
