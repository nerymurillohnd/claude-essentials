#!/usr/bin/env node
// Runs Claude Code's official validator in strict mode (warnings are errors) on the
// marketplace manifest and on EVERY plugin: validating the marketplace root does not
// check plugin contents (skills, agents, commands, hooks). Resolves DEBT-0001.
// The only tolerated finding is the empty-marketplace warning while plugins/ is empty.
import { readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { parse } from "yaml";
import { collectFindings, EMPTY_MARKETPLACE_WARNING, runClaude } from "./lib/claude-cli.mjs";
import { listPluginDirs, pluginsDir, rootDir } from "./lib/plugins.mjs";

// CI pins the CLI (DEBT-0004); locally `claude` is whatever the maintainer runs.
// A mismatch is not an error, but results may differ from CI, so say so.
const ciVersion = parse(readFileSync(join(rootDir, ".github", "workflows", "ci.yml"), "utf8"))?.env
  ?.CLAUDE_CODE_VERSION;
const localVersion = runClaude(["--version"]).stdout.trim().split(/\s+/)[0];
if (ciVersion && localVersion && localVersion !== String(ciVersion)) {
  console.log(
    `note: local claude ${localVersion} differs from CI's CLAUDE_CODE_VERSION ${ciVersion}; results may differ from CI`,
  );
}

const pluginNames = listPluginDirs();
const targets = [".", ...pluginNames.map((name) => relative(rootDir, join(pluginsDir, name)))];
let failures = 0;

for (const target of targets) {
  const label = `claude plugin validate ${target} --strict`;
  const { status, stdout, stderr } = runClaude([
    "plugin",
    "validate",
    target,
    "--strict",
    "--json",
  ]);
  let report;
  try {
    report = JSON.parse(stdout);
  } catch {
    console.error(`✗ ${label}: unparseable output (exit ${status})\n${stderr}`);
    failures += 1;
    continue;
  }
  const all = collectFindings(report);
  const tolerated = (finding) =>
    target === "." && pluginNames.length === 0 && finding.message === EMPTY_MARKETPLACE_WARNING;
  const findings = all.filter((finding) => !tolerated(finding));
  const passed = findings.length === 0 && (status === 0 || all.length > 0);
  if (passed) {
    console.log(`✓ ${label}`);
    continue;
  }
  failures += 1;
  console.error(`✗ ${label}`);
  for (const finding of findings) {
    const file = finding.file ? relative(rootDir, finding.file) : target;
    console.error(`  - [${finding.severity}] ${file} ${finding.path ?? ""}: ${finding.message}`);
  }
}

if (failures > 0) process.exit(1);
