// @ts-check
// Text files must not carry raw control characters. An editor or tool can turn a
// written escape (a backslash-u NUL escape) into the byte itself; that silently breaks jq
// programs, JSON, and Markdown, and it happened twice while building block-no-verify.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { extname, join } from "node:path";
import { test } from "node:test";
import { rootDir } from "./plugins.mjs";

const textExtensions = new Set([
  ".md",
  ".json",
  ".jsonc",
  ".sh",
  ".mjs",
  ".js",
  ".yml",
  ".yaml",
  ".txt",
]);
// Anything below 0x20 except tab, line feed, and carriage return, plus DEL.
const control = new RegExp(
  `[${String.fromCharCode(0)}-${String.fromCharCode(8)}${String.fromCharCode(11, 12)}${String.fromCharCode(14)}-${String.fromCharCode(31)}${String.fromCharCode(127)}]`,
);

test("tracked and new text files contain no raw control characters", () => {
  const files = execFileSync(
    "git",
    ["ls-files", "-z", "--cached", "--others", "--exclude-standard"],
    {
      cwd: rootDir,
      encoding: "utf8",
    },
  )
    .split("\0")
    .filter(
      (file) => file !== "" && (textExtensions.has(extname(file)) || file.endsWith("LICENSE")),
    );
  assert.ok(files.length > 0);
  const offenders = [];
  for (const file of files) {
    let text;
    try {
      text = readFileSync(join(rootDir, file), "utf8");
    } catch {
      continue; // listed but deleted in the working tree
    }
    const lines = text.split("\n");
    const index = lines.findIndex((line) => control.test(line));
    if (index !== -1) offenders.push(`${file}:${index + 1}`);
  }
  assert.deepEqual(offenders, [], `raw control characters in: ${offenders.join(", ")}`);
});
