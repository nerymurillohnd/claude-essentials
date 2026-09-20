// @ts-check
// Validates .claude-plugin/marketplace.json and every plugins/*/.claude-plugin/plugin.json
// against schemas/*.schema.json, and cross-checks that every plugin listed in the
// marketplace catalog actually exists on disk (and vice versa), and that every
// catalog entry equals what npm run generate would write from its plugin.json.
import { join } from "node:path";
import { catalogEntryDrift, compileSchemas } from "./lib/catalog.mjs";
import { errorMessage } from "./lib/errors.mjs";
import {
  checkPluginKind,
  listPluginDirs,
  manifestPath,
  readJson,
  rootDir,
} from "./lib/plugins.mjs";
import { validateReadmes } from "./lib/readme-contract.mjs";
import { validateRepoMetadata } from "./lib/repo-metadata.mjs";

const marketplacePath = join(rootDir, ".claude-plugin", "marketplace.json");

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

  const schemas = compileSchemas();
  const marketplaceSchema = schemas.marketplace;
  // Cast is sound: schemas/plugin.schema.json requires a string "name", the only field
  // this script reads by name after validation.
  const pluginSchema = /** @type {PluginValidator} */ (schemas.plugin);

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

  const validPlugins = pluginDirs.filter((name) => !errors.includes(name));
  const entryProblems = catalogEntryDrift(
    marketplace.plugins ?? [],
    new Map(validPlugins.map((name) => [name, readJson(manifestPath(name))])),
  );
  for (const problem of entryProblems) console.error(`✗ ${problem}`);
  errors.push(...entryProblems);
  if (entryProblems.length === 0)
    console.log("✓ every catalog entry matches its plugin.json (description, category, tags)");

  const metadataProblems = validateRepoMetadata(rootDir, pluginDirs);
  for (const problem of metadataProblems) console.error(`✗ ${problem}`);
  errors.push(...metadataProblems);
  if (metadataProblems.length === 0)
    console.log(
      "✓ labels, issue forms, and workflow CLAUDE_CODE_VERSION pins pass metadata checks",
    );

  const readmeProblems = validateReadmes(rootDir, pluginDirs);
  for (const problem of readmeProblems) console.error(`✗ ${problem}`);
  errors.push(...readmeProblems);
  if (readmeProblems.length === 0)
    console.log(
      "✓ plugin READMEs follow the template contract; the root catalog lists every plugin",
    );

  if (errors.length > 0) {
    console.error(`\n${errors.length} problem(s) found.`);
    process.exit(1);
  }
  console.log(`\nAll good — ${pluginDirs.length} plugin(s) validated.`);
}

main();
