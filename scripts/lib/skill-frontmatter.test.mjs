// @ts-check
// A skill's `description` and `when_to_use` are what Claude Code loads to decide
// whether to invoke the skill, so the frontmatter must be parseable YAML and fit
// the documented budget. Both failures are silent: `claude plugin validate
// --strict` accepted a plain scalar containing ": " (invalid YAML) on
// 2026-09-20, and an over-budget description is truncated at startup with only a
// warning.
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { basename, join } from "node:path";
import { test } from "node:test";
import { parse } from "yaml";
import { listPluginDirs, pluginsDir } from "./plugins.mjs";

/** Combined cap on `description` + `when_to_use`, raised from 250 in 2.1.105. */
const LISTING_BUDGET = 1536;

/** @returns {string[]} every plugins/<id>/skills/<name>/SKILL.md on disk */
function listSkillFiles() {
  /** @type {string[]} */
  const files = [];
  for (const plugin of listPluginDirs()) {
    const skillsDir = join(pluginsDir, plugin, "skills");
    let entries;
    try {
      entries = readdirSync(skillsDir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      if (entry.isDirectory()) files.push(join(skillsDir, entry.name, "SKILL.md"));
    }
  }
  return files;
}

/**
 * @param {string} file
 * @returns {Record<string, unknown>}
 */
function readFrontmatter(file) {
  const match = /^---\n([\s\S]*?)\n---/.exec(readFileSync(file, "utf8"));
  assert.ok(match, `${file}: no YAML frontmatter block`);
  const body = match[1];
  assert.ok(body !== undefined, `${file}: empty YAML frontmatter block`);
  return /** @type {Record<string, unknown>} */ (parse(body));
}

const skillFiles = listSkillFiles();

test("every plugin ships at least one skill file to check", () => {
  assert.ok(skillFiles.length > 0, "no SKILL.md found under plugins/*/skills/");
});

for (const file of skillFiles) {
  const label = `${basename(join(file, "..", "..", ".."))}/${basename(join(file, ".."))}`;

  test(`${label}: frontmatter is valid YAML with a string description`, () => {
    const front = readFrontmatter(file);
    assert.equal(
      typeof front["description"],
      "string",
      `${file}: description must parse as a string`,
    );
    if ("when_to_use" in front) {
      assert.equal(
        typeof front["when_to_use"],
        "string",
        `${file}: when_to_use must parse as a string`,
      );
    }
  });

  test(`${label}: description and when_to_use fit the listing budget`, () => {
    const front = readFrontmatter(file);
    const description = String(front["description"]);
    const whenToUse = "when_to_use" in front ? String(front["when_to_use"]) : "";
    const total = description.length + whenToUse.length;
    assert.ok(
      total <= LISTING_BUDGET,
      `${file}: description + when_to_use is ${total} chars, over the ${LISTING_BUDGET} cap`,
    );
  });
}
