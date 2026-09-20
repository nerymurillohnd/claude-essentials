// @ts-check
// Every `<PREFIX>_TEST_BASH` variable a plugin README tells maintainers to set
// must be read by one of that plugin's own test-*.sh suites; otherwise the
// documented command silently tests the wrong shell (DEBT-0017).
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { test } from "node:test";
import { pluginsDir, rootDir } from "./plugins.mjs";

/** @param {string} dir @returns {string[]} */
function testScripts(dir) {
  return readdirSync(dir, { withFileTypes: true, recursive: true })
    .filter((entry) => entry.isFile() && /^test-.*\.sh$/.test(entry.name))
    .map((entry) => join(entry.parentPath, entry.name));
}

test("each README test-shell variable is read by that plugin's suites", () => {
  const plugins = readdirSync(pluginsDir, { withFileTypes: true }).filter((entry) =>
    entry.isDirectory(),
  );
  for (const plugin of plugins) {
    const dir = join(pluginsDir, plugin.name);
    const readme = readFileSync(join(dir, "README.md"), "utf8");
    const named = new Set(readme.match(/\b[A-Z][A-Z0-9]*_TEST_BASH\b/g) ?? []);
    if (named.size === 0) continue;
    const suites = testScripts(dir).map((file) => readFileSync(file, "utf8"));
    for (const variable of named) {
      assert.ok(
        suites.some((source) => source.includes(variable)),
        `${relative(rootDir, join(dir, "README.md"))} names ${variable}, but no test-*.sh in plugins/${plugin.name} reads it`,
      );
    }
  }
});
