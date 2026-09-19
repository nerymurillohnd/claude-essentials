#!/usr/bin/env bash
# Workspace for the case: a change whose tests are green but miss the requirement.
set -euo pipefail
cat >package.json <<'JSON'
{ "name": "sum-demo", "version": "1.0.0", "type": "module", "scripts": { "test": "node --test" } }
JSON
cat >sum.js <<'JS'
// Requirement: sum(a, b) must return the arithmetic sum, including negative numbers.
export function sum(a, b) {
  if (a < 0 || b < 0) return Math.abs(a) + Math.abs(b);
  return a + b;
}
JS
cat >sum.test.js <<'JS'
import assert from "node:assert/strict";
import { test } from "node:test";
import { sum } from "./sum.js";

test("adds positive numbers", () => {
  assert.equal(sum(2, 3), 5);
});
JS
