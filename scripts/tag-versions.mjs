#!/usr/bin/env node
// Tags every plugin version that has no "{name}--v{version}" tag yet (ADR-0003),
// using the official `claude plugin tag --push`: it validates the plugin, checks
// plugin.json against the marketplace entry, and refuses dirty trees or existing
// tags. Plugins are not packages — the tag is the release; notes live in CHANGELOG.md.
// Idempotent. Usage: node scripts/tag-versions.mjs [--dry-run]
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { parseArgs } from "node:util";
import { runClaude } from "./lib/claude-cli.mjs";
import { listPluginDirs, manifestPath, pluginsDir, readJson, rootDir } from "./lib/plugins.mjs";
import { untaggedVersions } from "./lib/version-plan.mjs";

const { values } = parseArgs({ options: { "dry-run": { type: "boolean", default: false } } });

const plugins = listPluginDirs().map((name) => {
  const changelogPath = join(pluginsDir, name, "CHANGELOG.md");
  return {
    name,
    version: readJson(manifestPath(name)).version,
    changelog: existsSync(changelogPath) ? readFileSync(changelogPath, "utf8") : null,
  };
});
const tags = new Set(
  execFileSync("git", ["tag", "--list", "*--v*"], { cwd: rootDir, encoding: "utf8" })
    .split("\n")
    .filter(Boolean),
);
const { versions, errors } = untaggedVersions(plugins, tags);

for (const error of errors) console.error(`✗ ${error}`);
if (errors.length > 0) process.exit(1);
if (versions.length === 0) {
  console.log("Every plugin version is already tagged.");
  process.exit(0);
}

for (const { name, tag } of versions) {
  const mode = values["dry-run"] ? ["--dry-run"] : ["--push", "-m", `${name} v%s`];
  const { status, stdout, stderr } = runClaude(["plugin", "tag", `plugins/${name}`, ...mode]);
  process.stdout.write(stdout);
  if (status !== 0) {
    console.error(`✗ claude plugin tag failed for ${tag}\n${stderr}`);
    process.exit(1);
  }
}
