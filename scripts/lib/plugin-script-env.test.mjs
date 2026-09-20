// @ts-check
// A bundled script that reads an environment variable gives the user a control.
// A control the README does not mention is invisible: nobody can use it, and
// nobody reviewing the plugin knows the script's behavior can change underneath
// them. `agent-self-knowledge` shipped three such variables on 2026-09-20 and a
// full release review found two of them by hand and missed the third.
//
// Python only: `os.environ` names the variable unambiguously, while a shell
// `${VAR}` is far more often a local than an environment read.
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { test } from "node:test";
import { listPluginDirs, pluginsDir } from "./plugins.mjs";

/** Variables the environment provides, which a README need not document. */
const AMBIENT =
  /^(HOME|PATH|TMPDIR|TMP|TEMP|USER|SHELL|LANG|LC_[A-Z]+|PWD|XDG_[A-Z_]+|CLAUDE_[A-Z_]+|PYTHON[A-Z]*|NO_COLOR|CI)$/;

const ENV_READ = /os\.environ(?:\.get\(\s*|\[\s*)["']([A-Z][A-Z0-9_]*)["']/g;

/**
 * @param {string} dir
 * @returns {string[]}
 */
function walk(dir) {
  /** @type {string[]} */
  const found = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) found.push(...walk(path));
    else if (path.endsWith(".py")) found.push(path);
  }
  return found;
}

for (const plugin of listPluginDirs()) {
  const dir = join(pluginsDir, plugin);
  let scripts;
  try {
    scripts = statSync(dir).isDirectory() ? walk(dir) : [];
  } catch {
    continue;
  }
  if (scripts.length === 0) continue;

  test(`${plugin}: every environment variable its Python scripts read is in the README`, () => {
    const readme = readFileSync(join(dir, "README.md"), "utf8");
    /** @type {Map<string, string>} */
    const undocumented = new Map();
    for (const script of scripts) {
      const source = readFileSync(script, "utf8");
      for (const match of source.matchAll(ENV_READ)) {
        const name = match[1];
        if (name === undefined || AMBIENT.test(name)) continue;
        // Whole-word: a README naming FOO_BAR must not satisfy a read of FOO.
        const mentioned = new RegExp(`(?<![A-Z0-9_])${name}(?![A-Z0-9_])`).test(readme);
        if (!mentioned) undocumented.set(name, relative(dir, script));
      }
    }
    assert.deepEqual(
      [...undocumented].map(([name, script]) => `${name} (read in ${script})`),
      [],
      `plugins/${plugin}/README.md documents none of these environment variables`,
    );
  });
}
