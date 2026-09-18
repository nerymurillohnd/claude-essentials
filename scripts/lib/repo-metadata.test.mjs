import assert from "node:assert/strict";
import { test } from "node:test";
import { rootDir } from "./plugins.mjs";
import { checkLabels, validateRepoMetadata } from "./repo-metadata.mjs";

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

test("the committed .github/labels.json is valid", () => {
  assert.deepEqual(validateRepoMetadata(rootDir), []);
});
