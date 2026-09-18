#!/usr/bin/env node
// Validates .claude-plugin/marketplace.json and every plugins/*/.claude-plugin/plugin.json
// against schemas/*.schema.json, and cross-checks that every plugin listed in the
// marketplace catalog actually exists on disk (and vice versa).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import Ajv from "ajv";
import addFormats from "ajv-formats";
import {
  checkPluginKind,
  listPluginDirs,
  manifestPath,
  readJson,
  rootDir,
} from "./lib/plugins.mjs";
import { validateRepoMetadata } from "./lib/repo-metadata.mjs";

const marketplacePath = join(rootDir, ".claude-plugin", "marketplace.json");

const ajv = new Ajv({ allErrors: true, strict: false });
addFormats(ajv);

function loadSchema(name) {
  return JSON.parse(readFileSync(join(rootDir, "schemas", name), "utf8"));
}

function reportErrors(label, errors) {
  console.error(`✗ ${label}`);
  for (const err of errors) {
    console.error(`  - ${err.instancePath || "/"} ${err.message}`);
  }
}

function main() {
  const errors = [];

  const marketplaceSchema = ajv.compile(loadSchema("marketplace.schema.json"));
  const pluginSchema = ajv.compile(loadSchema("plugin.schema.json"));

  const marketplace = readJson(marketplacePath);
  if (!marketplaceSchema(marketplace)) {
    reportErrors(".claude-plugin/marketplace.json", marketplaceSchema.errors);
    errors.push("marketplace.json");
  } else {
    console.log("✓ .claude-plugin/marketplace.json matches schema");
  }

  const pluginDirs = listPluginDirs();
  const catalogNames = new Set(marketplace.plugins?.map((p) => p.name) ?? []);
  const diskNames = new Set(pluginDirs);

  for (const name of pluginDirs) {
    let manifest;
    try {
      manifest = readJson(manifestPath(name));
    } catch (error) {
      console.error(
        `✗ plugins/${name}: cannot read/parse .claude-plugin/plugin.json (${error.message})`,
      );
      errors.push(name);
      continue;
    }
    if (!pluginSchema(manifest)) {
      reportErrors(`plugins/${name}/.claude-plugin/plugin.json`, pluginSchema.errors);
      errors.push(name);
      continue;
    }
    if (manifest.name !== name) {
      console.error(
        `✗ plugins/${name}: manifest name "${manifest.name}" must equal directory name`,
      );
      errors.push(name);
      continue;
    }
    const kindProblem = checkPluginKind(name, manifest);
    if (kindProblem) {
      console.error(`✗ ${kindProblem}`);
      errors.push(name);
      continue;
    }
    console.log(`✓ plugins/${name}/.claude-plugin/plugin.json matches schema and README Kind`);
  }

  for (const name of catalogNames) {
    if (!diskNames.has(name)) {
      console.error(`✗ marketplace.json lists "${name}" but plugins/${name} does not exist`);
      errors.push(name);
    }
  }
  for (const name of diskNames) {
    if (!catalogNames.has(name)) {
      console.error(
        `✗ plugins/${name} exists but is missing from marketplace.json — run npm run generate`,
      );
      errors.push(name);
    }
  }

  const metadataProblems = validateRepoMetadata(rootDir, pluginDirs);
  for (const problem of metadataProblems) console.error(`✗ ${problem}`);
  errors.push(...metadataProblems);
  if (metadataProblems.length === 0)
    console.log(
      "✓ labels, issue forms, and workflow CLAUDE_CODE_VERSION pins pass metadata checks",
    );

  if (errors.length > 0) {
    console.error(`\n${errors.length} problem(s) found.`);
    process.exit(1);
  }
  console.log(`\nAll good — ${pluginDirs.length} plugin(s) validated.`);
}

main();
