// @ts-check
import assert from "node:assert/strict";
import { test } from "node:test";
import { parse } from "yaml";
import {
  CATALOG_OPTION,
  pluginDropdownOptions,
  UNSURE_OPTION,
  withPluginOptions,
} from "./issue-forms.mjs";

const form = `name: Bug report
description: x
labels:
  - "type: bug"
body:
  - type: markdown
    attributes:
      value: |
        Hello \`x\`
  - type: dropdown
    id: plugin
    attributes:
      label: Affected plugin
      options:
        - stale
    validations:
      required: true
`;

test("pluginDropdownOptions brackets plugin names with catalog and unsure options", () => {
  assert.deepEqual(pluginDropdownOptions(["a", "b"]), [CATALOG_OPTION, "a", "b", UNSURE_OPTION]);
});

test("withPluginOptions rewrites only the plugin dropdown and keeps everything else", () => {
  const out = withPluginOptions(form, ["demo"]);
  const parsed = parse(out);
  assert.deepEqual(parsed.body[1].attributes.options, [CATALOG_OPTION, "demo", UNSURE_OPTION]);
  assert.equal(parsed.body[0].attributes.value, "Hello `x`\n");
  assert.deepEqual(parsed.labels, ["type: bug"]);
  assert.match(out, /- "type: bug"/);
});

test("withPluginOptions is idempotent", () => {
  const once = withPluginOptions(form, ["demo"]);
  assert.equal(withPluginOptions(once, ["demo"]), once);
});

test("withPluginOptions leaves forms without a plugin dropdown untouched", () => {
  const plain = "name: Docs\ndescription: x\nbody:\n  - type: input\n    id: where\n";
  assert.equal(withPluginOptions(plain, ["demo"]), plain);
});
