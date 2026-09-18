#!/usr/bin/env node
// Enforces ADR-0003 on the current branch: every plugin changed since the merge
// base with --base must bump its semver "version" and add a dated CHANGELOG.md
// entry, unless --deferred (the "bump: deferred" PR label) is passed.
// --verify-tag also runs the official `claude plugin tag <dir> --dry-run` for each
// new/bumped plugin (needs a clean working tree — CI passes it).
// Usage: node scripts/check-versions.mjs [--base origin/main] [--deferred] [--verify-tag] [--json]
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { parseArgs } from "node:util";
import { runClaude } from "./lib/claude-cli.mjs";
import { manifestPath, pluginsDir, readJson, rootDir } from "./lib/plugins.mjs";
import { planVersions, pluginsTouched } from "./lib/version-plan.mjs";

const { values } = parseArgs({
  options: {
    base: { type: "string", default: "origin/main" },
    deferred: { type: "boolean", default: false },
    "verify-tag": { type: "boolean", default: false },
    json: { type: "boolean", default: false },
  },
});

const git = (...args) =>
  execFileSync("git", args, { cwd: rootDir, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
const lines = (text) => text.split("\n").filter(Boolean);

function showAt(ref, path) {
  try {
    return git("show", `${ref}:${path}`);
  } catch {
    return null;
  }
}

const mergeBase = git("merge-base", values.base, "HEAD").trim();
const changedFiles = [
  ...new Set([
    ...lines(git("diff", "--name-only", "--no-renames", mergeBase)),
    ...lines(git("ls-files", "--others", "--exclude-standard", "--", "plugins")),
  ]),
];

const base = new Map();
const head = new Map();
const changelogs = new Map();
for (const name of pluginsTouched(changedFiles)) {
  const before = showAt(mergeBase, `plugins/${name}/.claude-plugin/plugin.json`);
  base.set(name, before ? JSON.parse(before) : null);
  head.set(name, existsSync(manifestPath(name)) ? readJson(manifestPath(name)) : null);
  const changelogPath = join(pluginsDir, name, "CHANGELOG.md");
  changelogs.set(name, existsSync(changelogPath) ? readFileSync(changelogPath, "utf8") : null);
}

const marketplace = readJson(join(rootDir, ".claude-plugin", "marketplace.json"));
const plan = planVersions({
  changedFiles,
  base,
  head,
  changelogs,
  renames: marketplace.renames ?? {},
  existingTags: new Set(lines(git("tag", "--list", "*--v*"))),
  deferred: values.deferred,
});

if (values["verify-tag"]) {
  for (const plugin of plan.plugins) {
    if (plugin.errors.length > 0 || !["new", "bumped"].includes(plugin.status)) continue;
    const { status, stdout, stderr } = runClaude([
      "plugin",
      "tag",
      `plugins/${plugin.name}`,
      "--dry-run",
    ]);
    if (status !== 0) {
      plugin.errors.push(`claude plugin tag --dry-run failed:\n${`${stdout}\n${stderr}`.trim()}`);
    }
  }
  plan.ok = plan.plugins.every((plugin) => plugin.errors.length === 0);
  if (!plan.ok) plan.bumpLabel = null;
}

if (values.json) {
  console.log(JSON.stringify(plan, null, 2));
} else {
  if (plan.plugins.length === 0) console.log(`No plugin changes since ${values.base}.`);
  for (const plugin of plan.plugins) {
    const versions = `${plugin.from ?? "∅"} → ${plugin.to ?? "∅"}`;
    console.log(
      `${plugin.errors.length ? "✗" : "✓"} ${plugin.name}: ${plugin.status} (${versions})`,
    );
    for (const error of plugin.errors) console.error(`  - ${error}`);
  }
  console.log(plan.bumpLabel ? `\nComputed label: ${plan.bumpLabel}` : "\nRelease check failed.");
}
process.exit(plan.ok ? 0 : 1);
