// @ts-check
import assert from "node:assert/strict";
import { test } from "node:test";
import { errorMessage, hasErrorCode } from "./errors.mjs";

test("hasErrorCode matches Node system errors by code only", () => {
  const enoent = Object.assign(new Error("missing"), { code: "ENOENT" });
  assert.equal(hasErrorCode(enoent, "ENOENT"), true);
  assert.equal(hasErrorCode(enoent, "EACCES"), false);
  assert.equal(hasErrorCode(new Error("plain"), "ENOENT"), false);
  assert.equal(hasErrorCode({ code: "ENOENT" }, "ENOENT"), false);
  assert.equal(hasErrorCode("ENOENT", "ENOENT"), false);
});

test("errorMessage prints Error messages and stringifies anything else", () => {
  assert.equal(errorMessage(new Error("boom")), "boom");
  assert.equal(errorMessage("text"), "text");
  assert.equal(errorMessage(42), "42");
  assert.equal(errorMessage(undefined), "undefined");
});
