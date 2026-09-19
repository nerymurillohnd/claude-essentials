// @ts-check
// Validates .claude-plugin/marketplace.json and every plugins/*/.claude-plugin/plugin.json
// against schemas/*.schema.json, and cross-checks that every plugin listed in the
// marketplace catalog actually exists on disk (and vice versa).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { Ajv } from "ajv";
import ajvFormats from "ajv-formats";
import { errorMessage } from "./lib/errors.mjs";
import {
  checkPluginKind,
  listPluginDirs,
  manifestPath,
  readJson,
  rootDir,
} from "./lib/plugins.mjs";
import { validateRepoMetadata } from "./lib/repo-metadata.mjs";

// ajv-formats is CommonJS: `.default` is the plugin function (same object at runtime) and what its typings declare.
const addFormats = ajvFormats.default;

const marketplacePath = join(rootDir, ".claude-plugin", "marketplace.json");

const ajv = new Ajv({ allErrors: true, strict: false });
addFormats(ajv);

/** @param {string} name */
function loadSchema(name) {
  return JSON.parse(readFileSync(join(rootDir, "schemas", name), "utf8"));
}

/**
 * @param {string} label
 * @param {import("ajv").ErrorObject[] | null | undefined} errors
 */
function reportErrors(label, errors) {
  console.error(`✗ ${label}`);
  for (const err of errors ?? []) {
    console.error(`  - ${err.instancePath || "/"} ${err.message}`);
  }
}

/** @typedef {import("ajv").ValidateFunction<{ name: string } & Record<string, unknown>>} PluginValidator */

/**
 * Validates plugins/<name>/.claude-plugin/plugin.json and prints the outcome.
 * @param {string} name
 * @param {PluginValidator} pluginSchema
 * @returns {boolean} Whether the plugin passed every check.
 */
function validatePlugin(name, pluginSchema) {
  /** @type {unknown} */
  let manifest;
  try {
    manifest = readJson(manifestPath(name));
  } catch (error) {
    console.error(
      `✗ plugins/${name}: cannot read/parse .claude-plugin/plugin.json (${errorMessage(error)})`,
    );
    return false;
  }
  if (!pluginSchema(manifest)) {
    reportErrors(`plugins/${name}/.claude-plugin/plugin.json`, pluginSchema.errors);
    return false;
  }
  if (manifest.name !== name) {
    console.error(`✗ plugins/${name}: manifest name "${manifest.name}" must equal directory name`);
    return false;
  }
  const kindProblem = checkPluginKind(name, manifest);
  if (kindProblem) {
    console.error(`✗ ${kindProblem}`);
    return false;
  }
  console.log(`✓ plugins/${name}/.claude-plugin/plugin.json matches schema and README Kind`);
  return true;
}

/**
 * Names present in only one of the catalog and plugins/; prints each mismatch.
 * @param {ReadonlySet<string>} catalogNames
 * @param {ReadonlySet<string>} diskNames
 * @returns {string[]}
 */
function catalogDrift(catalogNames, diskNames) {
  const missingOnDisk = [...catalogNames].filter((name) => !diskNames.has(name));
  const missingInCatalog = [...diskNames].filter((name) => !catalogNames.has(name));
  for (const name of missingOnDisk) {
    console.error(`✗ marketplace.json lists "${name}" but plugins/${name} does not exist`);
  }
  for (const name of missingInCatalog) {
    console.error(
      `✗ plugins/${name} exists but is missing from marketplace.json — run npm run generate`,
    );
  }
  return [...missingOnDisk, ...missingInCatalog];
}

function main() {
  /** @type {string[]} */
  const errors = [];

  const marketplaceSchema = ajv.compile(loadSchema("marketplace.schema.json"));
  // Cast is sound: schemas/plugin.schema.json requires a string "name", the only field
  // this script reads by name after validation.
  const pluginSchema = /** @type {PluginValidator} */ (
    ajv.compile(loadSchema("plugin.schema.json"))
  );

  const marketplace = readJson(marketplacePath);
  if (!marketplaceSchema(marketplace)) {
    reportErrors(".claude-plugin/marketplace.json", marketplaceSchema.errors);
    errors.push("marketplace.json");
  } else {
    console.log("✓ .claude-plugin/marketplace.json matches schema");
  }

  const pluginDirs = listPluginDirs();
  /** @type {Set<string>} */
  const catalogNames = new Set(
    marketplace.plugins?.map(/** @param {{ name: string }} p */ (p) => p.name) ?? [],
  );
  errors.push(...pluginDirs.filter((name) => !validatePlugin(name, pluginSchema)));
  errors.push(...catalogDrift(catalogNames, new Set(pluginDirs)));

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
